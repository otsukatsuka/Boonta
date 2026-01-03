"""Tests for base repository."""

from datetime import date

import pytest

from app.models import Race
from app.repositories.base import BaseRepository


class TestBaseRepository:
    """Tests for BaseRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session, test_race):
        """Retrieve entity by ID."""
        repo = BaseRepository(Race, db_session)

        result = await repo.get(test_race.id)

        assert result is not None
        assert result.id == test_race.id
        assert result.name == test_race.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, db_session):
        """Get with non-existent ID should return None."""
        repo = BaseRepository(Race, db_session)

        result = await repo.get(99999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, db_session):
        """Skip/limit pagination works correctly."""
        repo = BaseRepository(Race, db_session)

        # Create multiple races
        for i in range(5):
            await repo.create({
                "name": f"レース{i+1}",
                "date": date(2024, 12, i+1),
                "venue": "中山",
                "course_type": "芝",
                "distance": 2000,
                "grade": "G1",
            })

        # Test pagination
        all_races = await repo.get_all(skip=0, limit=100)
        assert len(all_races) == 5

        first_two = await repo.get_all(skip=0, limit=2)
        assert len(first_two) == 2

        last_two = await repo.get_all(skip=3, limit=2)
        assert len(last_two) == 2

    @pytest.mark.asyncio
    async def test_get_all_with_filters(self, db_session):
        """Filter by grade returns only matching races."""
        repo = BaseRepository(Race, db_session)

        # Create races with different grades
        await repo.create({
            "name": "G1レース",
            "date": date(2024, 12, 1),
            "venue": "中山",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })
        await repo.create({
            "name": "G3レース",
            "date": date(2024, 12, 2),
            "venue": "東京",
            "course_type": "芝",
            "distance": 1600,
            "grade": "G3",
        })

        g1_races = await repo.get_all(filters={"grade": "G1"})
        assert len(g1_races) == 1
        assert g1_races[0].grade == "G1"

        g3_races = await repo.get_all(filters={"grade": "G3"})
        assert len(g3_races) == 1
        assert g3_races[0].grade == "G3"

    @pytest.mark.asyncio
    async def test_count_with_filters(self, db_session):
        """Count with filters returns correct number."""
        repo = BaseRepository(Race, db_session)

        # Create races
        await repo.create({
            "name": "G1レース1",
            "date": date(2024, 12, 1),
            "venue": "中山",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })
        await repo.create({
            "name": "G1レース2",
            "date": date(2024, 12, 2),
            "venue": "東京",
            "course_type": "芝",
            "distance": 2400,
            "grade": "G1",
        })
        await repo.create({
            "name": "G3レース",
            "date": date(2024, 12, 3),
            "venue": "京都",
            "course_type": "芝",
            "distance": 1800,
            "grade": "G3",
        })

        total_count = await repo.count()
        assert total_count == 3

        g1_count = await repo.count(filters={"grade": "G1"})
        assert g1_count == 2

        g3_count = await repo.count(filters={"grade": "G3"})
        assert g3_count == 1

    @pytest.mark.asyncio
    async def test_create(self, db_session):
        """Create new entity and verify returned with ID."""
        repo = BaseRepository(Race, db_session)

        race = await repo.create({
            "name": "新規レース",
            "date": date(2024, 12, 25),
            "venue": "中山",
            "course_type": "芝",
            "distance": 2500,
            "grade": "G1",
        })

        assert race.id is not None
        assert race.name == "新規レース"
        assert race.distance == 2500

    @pytest.mark.asyncio
    async def test_update(self, db_session, test_race):
        """Update existing entity fields."""
        repo = BaseRepository(Race, db_session)

        updated = await repo.update(test_race.id, {
            "name": "更新されたレース名",
            "distance": 3000,
        })

        assert updated is not None
        assert updated.name == "更新されたレース名"
        assert updated.distance == 3000

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, db_session):
        """Update non-existent ID returns None."""
        repo = BaseRepository(Race, db_session)

        result = await repo.update(99999, {"name": "不存在"})

        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, db_session, test_race):
        """Delete entity returns True."""
        repo = BaseRepository(Race, db_session)

        result = await repo.delete(test_race.id)

        assert result is True

        # Verify deleted
        deleted = await repo.get(test_race.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db_session):
        """Delete non-existent ID returns False."""
        repo = BaseRepository(Race, db_session)

        result = await repo.delete(99999)

        assert result is False
