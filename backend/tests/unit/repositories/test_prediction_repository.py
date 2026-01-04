"""Tests for prediction repository."""

from datetime import datetime, timezone

import pytest

from app.models import Prediction
from app.repositories.prediction_repository import PredictionRepository


class TestPredictionRepository:
    """Tests for PredictionRepository specialized queries."""

    async def _create_prediction(
        self,
        db_session,
        race_id: int,
        model_version: str = "v1.0",
        predicted_at: datetime | None = None,
        confidence_score: float = 0.75,
    ) -> Prediction:
        """Helper to create a prediction."""
        prediction = Prediction(
            race_id=race_id,
            model_version=model_version,
            predicted_at=predicted_at or datetime.now(timezone.utc),
            prediction_data={
                "rankings": [
                    {"horse_number": 1, "score": 0.8},
                    {"horse_number": 2, "score": 0.6},
                ],
                "recommended_bets": [],
            },
            confidence_score=confidence_score,
            reasoning="テスト予測根拠",
        )
        db_session.add(prediction)
        await db_session.flush()
        return prediction

    @pytest.mark.asyncio
    async def test_get_by_race(self, db_session, test_race):
        """Get latest prediction for a race."""
        repo = PredictionRepository(db_session)

        # Create multiple predictions
        older = await self._create_prediction(
            db_session,
            test_race.id,
            predicted_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        )
        newer = await self._create_prediction(
            db_session,
            test_race.id,
            predicted_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        prediction = await repo.get_by_race(test_race.id)

        assert prediction is not None
        assert prediction.id == newer.id

    @pytest.mark.asyncio
    async def test_get_by_race_single(self, db_session, test_race):
        """Get prediction when only one exists."""
        repo = PredictionRepository(db_session)
        created = await self._create_prediction(db_session, test_race.id)

        prediction = await repo.get_by_race(test_race.id)

        assert prediction is not None
        assert prediction.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_race_none(self, db_session, test_race):
        """Get prediction for race with no predictions returns None."""
        repo = PredictionRepository(db_session)

        prediction = await repo.get_by_race(test_race.id)

        assert prediction is None

    @pytest.mark.asyncio
    async def test_get_by_race_nonexistent(self, db_session):
        """Get prediction for non-existent race returns None."""
        repo = PredictionRepository(db_session)

        prediction = await repo.get_by_race(99999)

        assert prediction is None

    @pytest.mark.asyncio
    async def test_get_history_by_race(self, db_session, test_race):
        """Get prediction history for a race."""
        repo = PredictionRepository(db_session)

        # Create predictions at different times
        for i in range(5):
            await self._create_prediction(
                db_session,
                test_race.id,
                predicted_at=datetime(2024, 1, 1, 10 + i, 0, tzinfo=timezone.utc),
                model_version=f"v1.{i}",
            )

        history = await repo.get_history_by_race(test_race.id, limit=10)

        assert len(history) == 5
        # Should be ordered by predicted_at descending
        for i in range(len(history) - 1):
            assert history[i].predicted_at > history[i + 1].predicted_at

    @pytest.mark.asyncio
    async def test_get_history_by_race_limit(self, db_session, test_race):
        """History respects limit parameter."""
        repo = PredictionRepository(db_session)

        for i in range(5):
            await self._create_prediction(
                db_session,
                test_race.id,
                predicted_at=datetime(2024, 1, 1, 10 + i, 0, tzinfo=timezone.utc),
            )

        history = await repo.get_history_by_race(test_race.id, limit=3)

        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_get_history_by_race_with_race_relation(self, db_session, test_race):
        """History includes race relation."""
        repo = PredictionRepository(db_session)
        await self._create_prediction(db_session, test_race.id)

        history = await repo.get_history_by_race(test_race.id, limit=10)

        assert len(history) == 1
        assert history[0].race is not None
        assert history[0].race.id == test_race.id

    @pytest.mark.asyncio
    async def test_get_history_by_race_empty(self, db_session, test_race):
        """History for race with no predictions returns empty list."""
        repo = PredictionRepository(db_session)

        history = await repo.get_history_by_race(test_race.id, limit=10)

        assert history == []

    @pytest.mark.asyncio
    async def test_get_latest_by_model_version(self, db_session, test_race):
        """Get latest predictions by model version."""
        repo = PredictionRepository(db_session)

        # Create predictions with different model versions
        await self._create_prediction(
            db_session, test_race.id, model_version="v1.0"
        )
        await self._create_prediction(
            db_session, test_race.id, model_version="v2.0"
        )
        await self._create_prediction(
            db_session, test_race.id, model_version="v2.0"
        )

        v2_predictions = await repo.get_latest_by_model_version("v2.0", limit=20)

        assert len(v2_predictions) == 2
        for pred in v2_predictions:
            assert pred.model_version == "v2.0"

    @pytest.mark.asyncio
    async def test_get_latest_by_model_version_limit(self, db_session, test_race):
        """Model version query respects limit."""
        repo = PredictionRepository(db_session)

        for i in range(5):
            await self._create_prediction(
                db_session,
                test_race.id,
                model_version="v1.0",
                predicted_at=datetime(2024, 1, 1, 10 + i, 0, tzinfo=timezone.utc),
            )

        predictions = await repo.get_latest_by_model_version("v1.0", limit=3)

        assert len(predictions) == 3

    @pytest.mark.asyncio
    async def test_get_latest_by_model_version_with_race(self, db_session, test_race):
        """Model version query includes race relation."""
        repo = PredictionRepository(db_session)
        await self._create_prediction(db_session, test_race.id, model_version="v1.0")

        predictions = await repo.get_latest_by_model_version("v1.0", limit=10)

        assert len(predictions) == 1
        assert predictions[0].race is not None

    @pytest.mark.asyncio
    async def test_get_latest_by_model_version_none(self, db_session, test_race):
        """No predictions for model version returns empty list."""
        repo = PredictionRepository(db_session)
        await self._create_prediction(db_session, test_race.id, model_version="v1.0")

        predictions = await repo.get_latest_by_model_version("v999.0", limit=10)

        assert predictions == []
