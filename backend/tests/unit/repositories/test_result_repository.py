"""Tests for result repository."""

from datetime import date

import pytest

from app.models import RaceResult
from app.repositories.result_repository import ResultRepository
from tests.fixtures.factories import create_race


class TestResultRepository:
    """Tests for ResultRepository specialized queries."""

    @pytest.mark.asyncio
    async def test_get_by_race(
        self, db_session, test_race, test_results
    ):
        """Get all results for a race."""
        repo = ResultRepository(db_session)

        results = await repo.get_by_race(test_race.id)

        assert len(results) == len(test_results)
        # Results should be ordered by position
        for i, result in enumerate(results, 1):
            assert result.position == i
            # Check relations are loaded
            assert result.horse is not None
            if result.jockey_id:
                assert result.jockey is not None

    @pytest.mark.asyncio
    async def test_get_by_race_empty(self, db_session, test_race):
        """Get results for race with no results returns empty list."""
        repo = ResultRepository(db_session)

        results = await repo.get_by_race(test_race.id)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_race_nonexistent(self, db_session):
        """Get results for non-existent race returns empty list."""
        repo = ResultRepository(db_session)

        results = await repo.get_by_race(99999)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_horse(
        self, db_session, test_race, test_horses, test_results
    ):
        """Get results for a horse."""
        repo = ResultRepository(db_session)
        horse = test_horses[0]

        results = await repo.get_by_horse(horse.id, limit=10)

        assert len(results) >= 1
        for result in results:
            assert result.horse_id == horse.id
            # Check relations are loaded
            assert result.race is not None

    @pytest.mark.asyncio
    async def test_get_by_horse_limit(
        self, db_session, test_race, test_horses, test_results
    ):
        """Get by horse respects limit."""
        repo = ResultRepository(db_session)
        horse = test_horses[0]

        # Create additional results for same horse
        for i in range(5):
            race = create_race(name=f"追加レース{i}", race_date=date(2024, 10, i + 1))
            db_session.add(race)
            await db_session.flush()
            result = RaceResult(
                race_id=race.id,
                horse_id=horse.id,
                position=i + 1,
                time=150.0,
            )
            db_session.add(result)
        await db_session.flush()

        results = await repo.get_by_horse(horse.id, limit=3)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_by_horse_no_results(self, db_session, test_horse):
        """Get results for horse with no results returns empty list."""
        repo = ResultRepository(db_session)

        results = await repo.get_by_horse(test_horse.id, limit=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_jockey(
        self, db_session, test_race, test_jockeys, test_results
    ):
        """Get results for a jockey."""
        repo = ResultRepository(db_session)
        jockey = test_jockeys[0]

        results = await repo.get_by_jockey(jockey.id, limit=50)

        assert len(results) >= 1
        for result in results:
            assert result.jockey_id == jockey.id
            # Check relations are loaded
            assert result.race is not None
            assert result.horse is not None

    @pytest.mark.asyncio
    async def test_get_by_jockey_no_results(self, db_session, test_jockey):
        """Get results for jockey with no results returns empty list."""
        repo = ResultRepository(db_session)

        results = await repo.get_by_jockey(test_jockey.id, limit=50)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_race_and_horse(
        self, db_session, test_race, test_horses, test_results
    ):
        """Get specific result by race and horse."""
        repo = ResultRepository(db_session)
        horse = test_horses[0]

        result = await repo.get_by_race_and_horse(test_race.id, horse.id)

        assert result is not None
        assert result.race_id == test_race.id
        assert result.horse_id == horse.id

    @pytest.mark.asyncio
    async def test_get_by_race_and_horse_not_found(
        self, db_session, test_race, test_results
    ):
        """Get result with non-existent horse returns None."""
        repo = ResultRepository(db_session)

        result = await repo.get_by_race_and_horse(test_race.id, 99999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_horse_with_conditions_distance(
        self, db_session, test_horses
    ):
        """Filter results by distance range."""
        repo = ResultRepository(db_session)
        horse = test_horses[0]

        # Create races with different distances
        race_2000 = create_race(name="2000mレース", distance=2000, race_date=date(2024, 6, 1))
        race_2400 = create_race(name="2400mレース", distance=2400, race_date=date(2024, 7, 1))
        race_1600 = create_race(name="1600mレース", distance=1600, race_date=date(2024, 8, 1))
        db_session.add_all([race_2000, race_2400, race_1600])
        await db_session.flush()

        for race in [race_2000, race_2400, race_1600]:
            result = RaceResult(race_id=race.id, horse_id=horse.id, position=1, time=150.0)
            db_session.add(result)
        await db_session.flush()

        # Search for 2000m (±200m range = 1800-2200m)
        results = await repo.get_by_horse_with_conditions(
            horse.id, distance=2000, limit=20
        )

        assert len(results) == 1
        assert results[0].race.distance == 2000

    @pytest.mark.asyncio
    async def test_get_by_horse_with_conditions_venue(
        self, db_session, test_horses
    ):
        """Filter results by venue."""
        repo = ResultRepository(db_session)
        horse = test_horses[0]

        # Create races at different venues
        race_nakayama = create_race(name="中山レース", venue="中山", race_date=date(2024, 6, 1))
        race_tokyo = create_race(name="東京レース", venue="東京", race_date=date(2024, 7, 1))
        db_session.add_all([race_nakayama, race_tokyo])
        await db_session.flush()

        for race in [race_nakayama, race_tokyo]:
            result = RaceResult(race_id=race.id, horse_id=horse.id, position=1, time=150.0)
            db_session.add(result)
        await db_session.flush()

        results = await repo.get_by_horse_with_conditions(
            horse.id, venue="中山", limit=20
        )

        assert len(results) == 1
        assert results[0].race.venue == "中山"

    @pytest.mark.asyncio
    async def test_get_by_horse_with_conditions_track_condition(
        self, db_session, test_horses
    ):
        """Filter results by track condition."""
        repo = ResultRepository(db_session)
        horse = test_horses[0]

        # Create races with different track conditions
        race_good = create_race(name="良馬場レース", track_condition="良", race_date=date(2024, 6, 1))
        race_heavy = create_race(name="重馬場レース", track_condition="重", race_date=date(2024, 7, 1))
        db_session.add_all([race_good, race_heavy])
        await db_session.flush()

        for race in [race_good, race_heavy]:
            result = RaceResult(race_id=race.id, horse_id=horse.id, position=1, time=150.0)
            db_session.add(result)
        await db_session.flush()

        results = await repo.get_by_horse_with_conditions(
            horse.id, track_condition="重", limit=20
        )

        assert len(results) == 1
        assert results[0].race.track_condition == "重"

    @pytest.mark.asyncio
    async def test_get_by_horse_with_conditions_multiple(
        self, db_session, test_horses
    ):
        """Filter results by multiple conditions."""
        repo = ResultRepository(db_session)
        horse = test_horses[0]

        # Create matching race
        race_match = create_race(
            name="条件一致レース",
            distance=2000,
            venue="中山",
            track_condition="良",
            race_date=date(2024, 6, 1),
        )
        # Create non-matching races
        race_nomatch1 = create_race(
            name="距離不一致",
            distance=1600,
            venue="中山",
            track_condition="良",
            race_date=date(2024, 7, 1),
        )
        race_nomatch2 = create_race(
            name="場所不一致",
            distance=2000,
            venue="東京",
            track_condition="良",
            race_date=date(2024, 8, 1),
        )
        db_session.add_all([race_match, race_nomatch1, race_nomatch2])
        await db_session.flush()

        for race in [race_match, race_nomatch1, race_nomatch2]:
            result = RaceResult(race_id=race.id, horse_id=horse.id, position=1, time=150.0)
            db_session.add(result)
        await db_session.flush()

        results = await repo.get_by_horse_with_conditions(
            horse.id,
            distance=2000,
            venue="中山",
            track_condition="良",
            limit=20,
        )

        assert len(results) == 1
        assert results[0].race.name == "条件一致レース"

    @pytest.mark.asyncio
    async def test_get_by_horse_with_conditions_no_conditions(
        self, db_session, test_race, test_horses, test_results
    ):
        """No conditions returns all results for horse."""
        repo = ResultRepository(db_session)
        horse = test_horses[0]

        results = await repo.get_by_horse_with_conditions(horse.id, limit=20)

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_get_by_horse_with_conditions_limit(
        self, db_session, test_horses
    ):
        """Conditions query respects limit."""
        repo = ResultRepository(db_session)
        horse = test_horses[0]

        # Create multiple races
        for i in range(5):
            race = create_race(name=f"レース{i}", race_date=date(2024, 6, i + 1))
            db_session.add(race)
            await db_session.flush()
            result = RaceResult(race_id=race.id, horse_id=horse.id, position=1, time=150.0)
            db_session.add(result)
        await db_session.flush()

        results = await repo.get_by_horse_with_conditions(horse.id, limit=3)

        assert len(results) == 3
