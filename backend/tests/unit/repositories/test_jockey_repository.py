"""Tests for jockey repository."""

import pytest

from app.repositories.jockey_repository import JockeyRepository
from tests.fixtures.factories import create_jockey


class TestJockeyRepository:
    """Tests for JockeyRepository specialized queries."""

    @pytest.mark.asyncio
    async def test_get_by_name(self, db_session, test_jockey):
        """Get jockey by exact name."""
        repo = JockeyRepository(db_session)

        jockey = await repo.get_by_name("C.ルメール")

        assert jockey is not None
        assert jockey.name == "C.ルメール"

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, db_session, test_jockey):
        """Get jockey by name that doesn't exist returns None."""
        repo = JockeyRepository(db_session)

        jockey = await repo.get_by_name("存在しない騎手")

        assert jockey is None

    @pytest.mark.asyncio
    async def test_get_by_name_partial_no_match(self, db_session, test_jockey):
        """Partial name doesn't match (exact match required)."""
        repo = JockeyRepository(db_session)

        jockey = await repo.get_by_name("ルメール")  # Missing "C."

        assert jockey is None

    @pytest.mark.asyncio
    async def test_search_by_name(self, db_session, test_jockeys):
        """Search jockeys by partial name."""
        repo = JockeyRepository(db_session)

        # Search for jockeys with "武" in name
        jockeys = await repo.search_by_name("武")

        # 武豊, 横山武史
        assert len(jockeys) >= 1
        for jockey in jockeys:
            assert "武" in jockey.name

    @pytest.mark.asyncio
    async def test_search_by_name_limit(self, db_session, test_jockeys):
        """Search respects limit parameter."""
        repo = JockeyRepository(db_session)

        jockeys = await repo.search_by_name("", limit=3)

        assert len(jockeys) <= 3

    @pytest.mark.asyncio
    async def test_search_by_name_no_match(self, db_session, test_jockeys):
        """Search with no matches returns empty list."""
        repo = JockeyRepository(db_session)

        jockeys = await repo.search_by_name("存在しない騎手名パターン")

        assert jockeys == []

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, db_session, test_jockey):
        """Get existing jockey without creating new one."""
        repo = JockeyRepository(db_session)

        jockey, created = await repo.get_or_create("C.ルメール")

        assert created is False
        assert jockey.id == test_jockey.id
        assert jockey.name == "C.ルメール"

    @pytest.mark.asyncio
    async def test_get_or_create_new(self, db_session):
        """Create new jockey when it doesn't exist."""
        repo = JockeyRepository(db_session)

        jockey, created = await repo.get_or_create(
            "新騎手",
            win_rate=0.10,
            place_rate=0.30,
            venue_win_rate=0.08,
        )

        assert created is True
        assert jockey.name == "新騎手"
        assert jockey.win_rate == 0.10
        assert jockey.place_rate == 0.30
        assert jockey.venue_win_rate == 0.08

    @pytest.mark.asyncio
    async def test_get_or_create_new_minimal(self, db_session):
        """Create new jockey with minimal data."""
        repo = JockeyRepository(db_session)

        jockey, created = await repo.get_or_create("最小騎手")

        assert created is True
        assert jockey.name == "最小騎手"

    @pytest.mark.asyncio
    async def test_get_or_create_multiple_calls(self, db_session):
        """Multiple get_or_create calls return same jockey."""
        repo = JockeyRepository(db_session)

        jockey1, created1 = await repo.get_or_create("テスト騎手", win_rate=0.15)
        jockey2, created2 = await repo.get_or_create("テスト騎手", win_rate=0.20)

        assert created1 is True
        assert created2 is False
        assert jockey1.id == jockey2.id
        # Original win_rate is preserved
        assert jockey2.win_rate == 0.15
