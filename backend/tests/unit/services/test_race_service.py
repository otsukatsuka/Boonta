"""Tests for race service."""

from datetime import date, timedelta

import pytest

from app.schemas import RaceCreate, RaceUpdate
from app.services.race_service import RaceService


class TestRaceService:
    """Tests for RaceService operations."""

    @pytest.mark.asyncio
    async def test_get_race(self, db_session, test_race):
        """Get a race by ID returns RaceResponse."""
        service = RaceService(db_session)

        response = await service.get_race(test_race.id)

        assert response is not None
        assert response.id == test_race.id
        assert response.name == test_race.name
        assert response.entries_count == 0

    @pytest.mark.asyncio
    async def test_get_race_with_entries_count(
        self, db_session, test_race, test_entries
    ):
        """Get race includes entries count."""
        service = RaceService(db_session)

        response = await service.get_race(test_race.id)

        assert response is not None
        assert response.entries_count == len(test_entries)

    @pytest.mark.asyncio
    async def test_get_race_nonexistent(self, db_session):
        """Get non-existent race returns None."""
        service = RaceService(db_session)

        response = await service.get_race(99999)

        assert response is None

    @pytest.mark.asyncio
    async def test_get_race_with_entries(
        self, db_session, test_race, test_entries
    ):
        """Get race with entries loaded."""
        service = RaceService(db_session)

        race = await service.get_race_with_entries(test_race.id)

        assert race is not None
        assert race.id == test_race.id
        assert len(race.entries) == len(test_entries)

    @pytest.mark.asyncio
    async def test_get_race_with_entries_nonexistent(self, db_session):
        """Get non-existent race returns None."""
        service = RaceService(db_session)

        race = await service.get_race_with_entries(99999)

        assert race is None

    @pytest.mark.asyncio
    async def test_get_races(self, db_session, test_race):
        """Get races with pagination."""
        service = RaceService(db_session)

        responses, total = await service.get_races(skip=0, limit=10)

        assert total >= 1
        assert len(responses) >= 1
        assert any(r.id == test_race.id for r in responses)

    @pytest.mark.asyncio
    async def test_get_races_with_grade_filter(self, db_session, test_race):
        """Get races filtered by grade."""
        service = RaceService(db_session)

        responses, total = await service.get_races(grade="G1")

        assert all(r.grade == "G1" for r in responses)

    @pytest.mark.asyncio
    async def test_get_races_with_pagination(self, db_session):
        """Get races respects skip and limit."""
        service = RaceService(db_session)

        # Create multiple races
        for i in range(5):
            await service.create_race(RaceCreate(
                name=f"テストレース{i}",
                date=date(2024, 10, i + 1),
                venue="中山",
                course_type="芝",
                distance=2000,
                grade="G1",
            ))

        # Get first 2
        first_page, _ = await service.get_races(skip=0, limit=2)
        # Get next 2
        second_page, _ = await service.get_races(skip=2, limit=2)

        assert len(first_page) == 2
        assert len(second_page) == 2
        # No overlap
        first_ids = {r.id for r in first_page}
        second_ids = {r.id for r in second_page}
        assert first_ids.isdisjoint(second_ids)

    @pytest.mark.asyncio
    async def test_get_races_by_date_range(self, db_session):
        """Get races within date range."""
        service = RaceService(db_session)

        # Create races on different dates
        await service.create_race(RaceCreate(
            name="12月レース",
            date=date(2024, 12, 15),
            venue="中山",
            course_type="芝",
            distance=2000,
            grade="G1",
        ))
        await service.create_race(RaceCreate(
            name="1月レース",
            date=date(2025, 1, 5),
            venue="京都",
            course_type="芝",
            distance=2000,
            grade="G1",
        ))

        responses = await service.get_races_by_date_range(
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
        )

        assert len(responses) == 1
        assert responses[0].name == "12月レース"

    @pytest.mark.asyncio
    async def test_get_races_by_date_range_with_grade(self, db_session):
        """Get races by date range with grade filter."""
        service = RaceService(db_session)

        await service.create_race(RaceCreate(
            name="G1レース",
            date=date(2024, 12, 15),
            venue="中山",
            course_type="芝",
            distance=2000,
            grade="G1",
        ))
        await service.create_race(RaceCreate(
            name="G3レース",
            date=date(2024, 12, 20),
            venue="阪神",
            course_type="芝",
            distance=1800,
            grade="G3",
        ))

        responses = await service.get_races_by_date_range(
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            grade="G1",
        )

        assert len(responses) == 1
        assert responses[0].grade == "G1"

    @pytest.mark.asyncio
    async def test_get_upcoming_races(self, db_session):
        """Get upcoming races."""
        service = RaceService(db_session)

        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        # Create past race
        await service.create_race(RaceCreate(
            name="過去レース",
            date=yesterday,
            venue="中山",
            course_type="芝",
            distance=2000,
            grade="G1",
        ))

        # Create future race
        await service.create_race(RaceCreate(
            name="未来レース",
            date=tomorrow,
            venue="東京",
            course_type="芝",
            distance=2000,
            grade="G1",
        ))

        responses = await service.get_upcoming_races(limit=10)

        # Should not include past race
        assert all(r.date >= today for r in responses)
        assert any(r.name == "未来レース" for r in responses)

    @pytest.mark.asyncio
    async def test_create_race(self, db_session):
        """Create a new race."""
        service = RaceService(db_session)

        data = RaceCreate(
            name="新規レース",
            date=date(2024, 11, 15),
            venue="東京",
            course_type="芝",
            distance=2400,
            grade="G1",
            track_condition="良",
            weather="晴",
            purse=30000,
        )

        response = await service.create_race(data)

        assert response is not None
        assert response.id is not None
        assert response.name == "新規レース"
        assert response.venue == "東京"
        assert response.distance == 2400
        assert response.entries_count == 0

    @pytest.mark.asyncio
    async def test_update_race(self, db_session, test_race):
        """Update an existing race."""
        service = RaceService(db_session)

        data = RaceUpdate(
            name="更新レース",
            distance=3000,
        )

        response = await service.update_race(test_race.id, data)

        assert response is not None
        assert response.name == "更新レース"
        assert response.distance == 3000
        # Unchanged fields preserved
        assert response.venue == test_race.venue

    @pytest.mark.asyncio
    async def test_update_race_nonexistent(self, db_session):
        """Update non-existent race returns None."""
        service = RaceService(db_session)

        data = RaceUpdate(name="更新レース")

        response = await service.update_race(99999, data)

        assert response is None

    @pytest.mark.asyncio
    async def test_update_race_partial(self, db_session, test_race):
        """Partial update only changes specified fields."""
        service = RaceService(db_session)

        original_name = test_race.name
        data = RaceUpdate(track_condition="重")

        response = await service.update_race(test_race.id, data)

        assert response is not None
        assert response.track_condition == "重"
        assert response.name == original_name

    @pytest.mark.asyncio
    async def test_delete_race(self, db_session, test_race):
        """Delete a race."""
        service = RaceService(db_session)

        result = await service.delete_race(test_race.id)

        assert result is True

        # Verify deletion
        response = await service.get_race(test_race.id)
        assert response is None

    @pytest.mark.asyncio
    async def test_delete_race_nonexistent(self, db_session):
        """Delete non-existent race returns False."""
        service = RaceService(db_session)

        result = await service.delete_race(99999)

        assert result is False

    @pytest.mark.asyncio
    async def test_search_races(self, db_session):
        """Search races by name."""
        service = RaceService(db_session)

        await service.create_race(RaceCreate(
            name="有馬記念",
            date=date(2024, 12, 22),
            venue="中山",
            course_type="芝",
            distance=2500,
            grade="G1",
        ))
        await service.create_race(RaceCreate(
            name="日本ダービー",
            date=date(2024, 5, 26),
            venue="東京",
            course_type="芝",
            distance=2400,
            grade="G1",
        ))

        responses = await service.search_races("記念")

        assert len(responses) >= 1
        assert any("記念" in r.name for r in responses)

    @pytest.mark.asyncio
    async def test_search_races_limit(self, db_session):
        """Search races respects limit."""
        service = RaceService(db_session)

        # Create multiple races with same pattern
        for i in range(5):
            await service.create_race(RaceCreate(
                name=f"テスト記念{i}",
                date=date(2024, 10, i + 1),
                venue="中山",
                course_type="芝",
                distance=2000,
                grade="G1",
            ))

        responses = await service.search_races("記念", limit=3)

        assert len(responses) <= 3

    @pytest.mark.asyncio
    async def test_search_races_no_match(self, db_session, test_race):
        """Search with no matches returns empty list."""
        service = RaceService(db_session)

        responses = await service.search_races("存在しないレース名")

        assert responses == []


class TestRaceServiceToResponse:
    """Tests for _to_response method."""

    @pytest.mark.asyncio
    async def test_to_response_includes_all_fields(
        self, db_session, test_race, test_entries
    ):
        """RaceResponse includes all expected fields."""
        service = RaceService(db_session)

        response = await service.get_race(test_race.id)

        assert response is not None
        assert response.id == test_race.id
        assert response.name == test_race.name
        assert response.date == test_race.date
        assert response.venue == test_race.venue
        assert response.course_type == test_race.course_type
        assert response.distance == test_race.distance
        assert response.track_condition == test_race.track_condition
        assert response.weather == test_race.weather
        assert response.grade == test_race.grade
        assert response.purse == test_race.purse
        assert response.entries_count == len(test_entries)
        assert response.created_at is not None
        assert response.updated_at is not None
