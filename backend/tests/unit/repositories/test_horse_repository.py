"""Tests for horse repository."""

import pytest

from app.repositories.horse_repository import HorseRepository
from tests.fixtures.factories import create_horse


class TestHorseRepository:
    """Tests for HorseRepository specialized queries."""

    @pytest.mark.asyncio
    async def test_get_by_name(self, db_session, test_horse):
        """Get horse by exact name."""
        repo = HorseRepository(db_session)

        horse = await repo.get_by_name("イクイノックス")

        assert horse is not None
        assert horse.name == "イクイノックス"

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, db_session, test_horse):
        """Get horse by name that doesn't exist returns None."""
        repo = HorseRepository(db_session)

        horse = await repo.get_by_name("存在しない馬")

        assert horse is None

    @pytest.mark.asyncio
    async def test_get_by_name_partial_no_match(self, db_session, test_horse):
        """Partial name doesn't match (exact match required)."""
        repo = HorseRepository(db_session)

        horse = await repo.get_by_name("イクイノ")  # Partial

        assert horse is None

    @pytest.mark.asyncio
    async def test_search_by_name(self, db_session, test_horses):
        """Search horses by partial name."""
        repo = HorseRepository(db_session)

        # Search for horses with "ド" in name
        horses = await repo.search_by_name("ド")

        # ドウデュース, ボルドグフーシュ, ヴェラアズール etc.
        assert len(horses) >= 1
        for horse in horses:
            assert "ド" in horse.name

    @pytest.mark.asyncio
    async def test_search_by_name_limit(self, db_session, test_horses):
        """Search respects limit parameter."""
        repo = HorseRepository(db_session)

        horses = await repo.search_by_name("", limit=5)

        assert len(horses) <= 5

    @pytest.mark.asyncio
    async def test_search_by_name_no_match(self, db_session, test_horses):
        """Search with no matches returns empty list."""
        repo = HorseRepository(db_session)

        horses = await repo.search_by_name("存在しない馬名パターン")

        assert horses == []

    @pytest.mark.asyncio
    async def test_get_with_results(
        self, db_session, test_race, test_horses, test_results
    ):
        """Get horse with race results loaded."""
        repo = HorseRepository(db_session)
        horse = test_horses[0]

        loaded = await repo.get_with_results(horse.id)

        assert loaded is not None
        assert loaded.results is not None
        assert len(loaded.results) >= 1
        # Check relations are loaded
        for result in loaded.results:
            assert result.race is not None

    @pytest.mark.asyncio
    async def test_get_with_results_no_results(self, db_session, test_horse):
        """Get horse with no results has empty results list."""
        repo = HorseRepository(db_session)

        loaded = await repo.get_with_results(test_horse.id)

        assert loaded is not None
        assert loaded.results == []

    @pytest.mark.asyncio
    async def test_get_with_results_nonexistent(self, db_session):
        """Get non-existent horse returns None."""
        repo = HorseRepository(db_session)

        loaded = await repo.get_with_results(99999)

        assert loaded is None

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, db_session, test_horse):
        """Get existing horse without creating new one."""
        repo = HorseRepository(db_session)

        horse, created = await repo.get_or_create("イクイノックス")

        assert created is False
        assert horse.id == test_horse.id
        assert horse.name == "イクイノックス"

    @pytest.mark.asyncio
    async def test_get_or_create_new(self, db_session):
        """Create new horse when it doesn't exist."""
        repo = HorseRepository(db_session)

        horse, created = await repo.get_or_create(
            "新馬",
            age=3,
            sex="牝",
            trainer="新調教師",
        )

        assert created is True
        assert horse.name == "新馬"
        assert horse.age == 3
        assert horse.sex == "牝"
        assert horse.trainer == "新調教師"

    @pytest.mark.asyncio
    async def test_get_or_create_new_minimal(self, db_session):
        """Create new horse with minimal data."""
        repo = HorseRepository(db_session)

        horse, created = await repo.get_or_create("最小馬")

        assert created is True
        assert horse.name == "最小馬"
