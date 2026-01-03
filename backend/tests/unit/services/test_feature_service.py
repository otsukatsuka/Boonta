"""Tests for feature service."""

from datetime import date

import pytest

from app.models import RaceResult
from app.services.feature_service import FeatureService


class TestBuildFeaturesForEntry:
    """Tests for build_features_for_entry method."""

    @pytest.mark.asyncio
    async def test_basic_features_extracted(
        self, db_session, test_race, test_entries, test_horses
    ):
        """Verify basic features are extracted from entry."""
        service = FeatureService(db_session)

        entry = test_entries[0]
        features = await service.build_features_for_entry(entry.id, test_race.date)

        assert features is not None
        assert "horse_age" in features
        assert "horse_weight" in features
        assert "horse_weight_diff" in features
        assert "odds" in features
        assert "popularity" in features
        assert "running_style" in features

    @pytest.mark.asyncio
    async def test_race_condition_features(
        self, db_session, test_race, test_entries
    ):
        """Verify race condition features are extracted."""
        service = FeatureService(db_session)

        entry = test_entries[0]
        features = await service.build_features_for_entry(entry.id, test_race.date)

        assert features is not None
        assert features["distance"] == test_race.distance
        assert features["course_type"] == test_race.course_type
        assert features["venue"] == test_race.venue
        assert features["track_condition"] == test_race.track_condition

    @pytest.mark.asyncio
    async def test_jockey_features(
        self, db_session, test_race, test_entries, test_jockeys
    ):
        """Verify jockey features are extracted."""
        service = FeatureService(db_session)

        entry = test_entries[0]
        features = await service.build_features_for_entry(entry.id, test_race.date)

        assert features is not None
        # Entry has jockey relation
        if entry.jockey_id:
            assert "jockey_win_rate" in features
            assert "jockey_venue_win_rate" in features

    @pytest.mark.asyncio
    async def test_nonexistent_entry_returns_none(self, db_session):
        """Nonexistent entry should return None."""
        service = FeatureService(db_session)

        features = await service.build_features_for_entry(99999, date(2024, 12, 22))
        assert features is None

    @pytest.mark.asyncio
    async def test_workout_features_included(
        self, db_session, test_race, test_entries
    ):
        """Verify workout evaluation is included."""
        service = FeatureService(db_session)

        entry = test_entries[0]
        features = await service.build_features_for_entry(entry.id, test_race.date)

        assert features is not None
        assert "workout_evaluation" in features


class TestBuildFeaturesForRace:
    """Tests for build_features_for_race method."""

    @pytest.mark.asyncio
    async def test_returns_dataframe(
        self, db_session, test_race, test_entries
    ):
        """Verify return type is DataFrame."""
        service = FeatureService(db_session)

        df = await service.build_features_for_race(test_race.id)

        assert df is not None
        assert len(df) > 0

    @pytest.mark.asyncio
    async def test_escape_and_front_count_added(
        self, db_session, test_race, test_entries
    ):
        """Verify escape_horse_count and front_horse_count columns are added."""
        service = FeatureService(db_session)

        df = await service.build_features_for_race(test_race.id)

        assert df is not None
        assert "escape_horse_count" in df.columns
        assert "front_horse_count" in df.columns

        # Should count ESCAPE and FRONT styles
        escape_count = sum(1 for e in test_entries if e.running_style == "ESCAPE")
        front_count = sum(1 for e in test_entries if e.running_style == "FRONT")

        assert df["escape_horse_count"].iloc[0] == escape_count
        assert df["front_horse_count"].iloc[0] == front_count

    @pytest.mark.asyncio
    async def test_entry_and_horse_ids_included(
        self, db_session, test_race, test_entries
    ):
        """Verify entry_id and horse_id columns are present."""
        service = FeatureService(db_session)

        df = await service.build_features_for_race(test_race.id)

        assert df is not None
        assert "entry_id" in df.columns
        assert "horse_id" in df.columns

    @pytest.mark.asyncio
    async def test_nonexistent_race_returns_none(self, db_session):
        """Nonexistent race should return None."""
        service = FeatureService(db_session)

        df = await service.build_features_for_race(99999)
        assert df is None


class TestBuildTrainingData:
    """Tests for build_training_data method."""

    @pytest.mark.asyncio
    async def test_combines_multiple_races(
        self, db_session, test_race, test_entries, test_results
    ):
        """Verify training data combines features from multiple races."""
        service = FeatureService(db_session)

        df = await service.build_training_data([test_race.id])

        assert df is not None
        # Should have entries with target variables
        assert "race_id" in df.columns

    @pytest.mark.asyncio
    async def test_adds_target_variables(
        self, db_session, test_race, test_entries, test_results
    ):
        """Verify position and is_place columns are added."""
        service = FeatureService(db_session)

        df = await service.build_training_data([test_race.id])

        assert df is not None
        assert "position" in df.columns
        assert "is_place" in df.columns

        # is_place should be 1 for top 3, 0 otherwise
        for _, row in df.iterrows():
            if row["position"] and row["position"] <= 3:
                assert row["is_place"] == 1
            elif row["position"] and row["position"] > 3:
                assert row["is_place"] == 0

    @pytest.mark.asyncio
    async def test_empty_race_ids_returns_none(self, db_session):
        """Empty race_ids list should return None."""
        service = FeatureService(db_session)

        df = await service.build_training_data([])
        assert df is None

    @pytest.mark.asyncio
    async def test_nonexistent_races_returns_none(self, db_session):
        """Nonexistent race IDs should return None."""
        service = FeatureService(db_session)

        df = await service.build_training_data([99999, 99998])
        assert df is None


class TestPastPerformanceFeatures:
    """Tests for past performance features extraction."""

    @pytest.mark.asyncio
    async def test_win_rate_calculation(
        self, db_session, test_race, test_entries, test_horses, test_results
    ):
        """Verify win rate is calculated correctly."""
        service = FeatureService(db_session)

        # Get an entry with results
        entry = test_entries[0]
        features = await service.build_features_for_entry(entry.id, test_race.date)

        assert features is not None
        # Win rate should be between 0 and 1
        if "win_rate" in features and features["win_rate"] is not None:
            assert 0 <= features["win_rate"] <= 1

    @pytest.mark.asyncio
    async def test_place_rate_calculation(
        self, db_session, test_race, test_entries, test_results
    ):
        """Verify place rate (top 3) is calculated correctly."""
        service = FeatureService(db_session)

        entry = test_entries[0]
        features = await service.build_features_for_entry(entry.id, test_race.date)

        assert features is not None
        # Place rate should be between 0 and 1
        if "place_rate" in features and features["place_rate"] is not None:
            assert 0 <= features["place_rate"] <= 1

    @pytest.mark.asyncio
    async def test_avg_position_last5(
        self, db_session, test_race, test_entries, test_results
    ):
        """Verify avg_position_last5 is calculated."""
        service = FeatureService(db_session)

        entry = test_entries[0]
        features = await service.build_features_for_entry(entry.id, test_race.date)

        assert features is not None
        # If there are results, avg position should be set
        if "avg_position_last5" in features and features["avg_position_last5"] is not None:
            assert features["avg_position_last5"] >= 1
