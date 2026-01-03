"""Tests for race repository."""

from datetime import date, timedelta

import pytest

from app.repositories.race_repository import RaceRepository


class TestRaceRepository:
    """Tests for RaceRepository specialized queries."""

    @pytest.mark.asyncio
    async def test_get_with_entries(self, db_session, test_race, test_entries):
        """Eagerly loads entries with horse and jockey."""
        repo = RaceRepository(db_session)

        race = await repo.get_with_entries(test_race.id)

        assert race is not None
        assert race.entries is not None
        assert len(race.entries) == len(test_entries)

        # Check that horse and jockey are loaded
        for entry in race.entries:
            assert entry.horse is not None
            # Jockey may or may not be set
            if entry.jockey_id:
                assert entry.jockey is not None

    @pytest.mark.asyncio
    async def test_get_with_entries_nonexistent(self, db_session):
        """Get with entries for non-existent race returns None."""
        repo = RaceRepository(db_session)

        race = await repo.get_with_entries(99999)

        assert race is None

    @pytest.mark.asyncio
    async def test_get_by_date_range(self, db_session):
        """Retrieve races within date range."""
        repo = RaceRepository(db_session)

        # Create races on different dates
        await repo.create({
            "name": "12月レース",
            "date": date(2024, 12, 15),
            "venue": "中山",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })
        await repo.create({
            "name": "1月レース",
            "date": date(2025, 1, 5),
            "venue": "京都",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })
        await repo.create({
            "name": "2月レース",
            "date": date(2025, 2, 10),
            "venue": "東京",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })

        # Get December races
        dec_races = await repo.get_by_date_range(
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
        )
        assert len(dec_races) == 1
        assert dec_races[0].name == "12月レース"

        # Get January-February races
        jan_feb_races = await repo.get_by_date_range(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 2, 28),
        )
        assert len(jan_feb_races) == 2

    @pytest.mark.asyncio
    async def test_get_by_date_range_with_grade_filter(self, db_session):
        """Filter by grade within date range."""
        repo = RaceRepository(db_session)

        # Create races with different grades
        await repo.create({
            "name": "G1レース",
            "date": date(2024, 12, 15),
            "venue": "中山",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })
        await repo.create({
            "name": "G3レース",
            "date": date(2024, 12, 20),
            "venue": "阪神",
            "course_type": "芝",
            "distance": 1800,
            "grade": "G3",
        })

        g1_races = await repo.get_by_date_range(
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            grade="G1",
        )
        assert len(g1_races) == 1
        assert g1_races[0].grade == "G1"

    @pytest.mark.asyncio
    async def test_get_upcoming_races(self, db_session):
        """Returns races with date >= today."""
        repo = RaceRepository(db_session)

        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)

        # Create past race
        await repo.create({
            "name": "過去レース",
            "date": yesterday,
            "venue": "中山",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })

        # Create future races
        await repo.create({
            "name": "明日レース",
            "date": tomorrow,
            "venue": "東京",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })
        await repo.create({
            "name": "来週レース",
            "date": next_week,
            "venue": "京都",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })

        upcoming = await repo.get_upcoming_races(limit=10)

        # Should not include past race
        assert all(race.date >= today for race in upcoming)
        assert len(upcoming) >= 2

    @pytest.mark.asyncio
    async def test_get_entries_count(self, db_session, test_race, test_entries):
        """Count entries for a race."""
        repo = RaceRepository(db_session)

        count = await repo.get_entries_count(test_race.id)

        assert count == len(test_entries)

    @pytest.mark.asyncio
    async def test_search_by_name(self, db_session):
        """Search by partial name match."""
        repo = RaceRepository(db_session)

        # Create races
        await repo.create({
            "name": "有馬記念",
            "date": date(2024, 12, 22),
            "venue": "中山",
            "course_type": "芝",
            "distance": 2500,
            "grade": "G1",
        })
        await repo.create({
            "name": "日本ダービー",
            "date": date(2024, 5, 26),
            "venue": "東京",
            "course_type": "芝",
            "distance": 2400,
            "grade": "G1",
        })
        await repo.create({
            "name": "天皇賞（秋）",
            "date": date(2024, 10, 27),
            "venue": "東京",
            "course_type": "芝",
            "distance": 2000,
            "grade": "G1",
        })

        # Search for "記念"
        results = await repo.search_by_name("記念")
        assert len(results) == 1
        assert "記念" in results[0].name

        # Search for "天皇"
        results = await repo.search_by_name("天皇")
        assert len(results) == 1
        assert "天皇" in results[0].name

    @pytest.mark.asyncio
    async def test_search_by_name_no_match(self, db_session):
        """Search with no matches returns empty list."""
        repo = RaceRepository(db_session)

        results = await repo.search_by_name("存在しないレース")

        assert len(results) == 0
