"""Tests for races API endpoints."""

from datetime import date, timedelta

import pytest


class TestRacesAPI:
    """Tests for /api/races endpoints."""

    @pytest.mark.asyncio
    async def test_get_races(self, client, test_race):
        """GET /api/races returns list of races."""
        response = await client.get("/api/races")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_races_with_pagination(self, client, db_session):
        """GET /api/races respects skip and limit."""
        # Create multiple races
        from app.models import Race
        from tests.fixtures.factories import create_race

        for i in range(5):
            race = create_race(name=f"テストレース{i}", race_date=date(2024, 10, i + 1))
            db_session.add(race)
        await db_session.commit()

        response = await client.get("/api/races?skip=0&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_races_with_grade_filter(self, client, test_race):
        """GET /api/races?grade=G1 filters by grade."""
        response = await client.get("/api/races?grade=G1")

        assert response.status_code == 200
        data = response.json()
        assert all(item["grade"] == "G1" for item in data["items"])

    @pytest.mark.asyncio
    async def test_get_race(self, client, test_race):
        """GET /api/races/{id} returns a race."""
        response = await client.get(f"/api/races/{test_race.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_race.id
        assert data["name"] == test_race.name

    @pytest.mark.asyncio
    async def test_get_race_not_found(self, client, db_session):
        """GET /api/races/{id} returns 404 for non-existent race."""
        response = await client.get("/api/races/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Race not found"

    @pytest.mark.asyncio
    async def test_get_upcoming_races(self, client, db_session):
        """GET /api/races/upcoming returns future races."""
        from app.models import Race
        from tests.fixtures.factories import create_race

        tomorrow = date.today() + timedelta(days=1)
        race = create_race(name="未来レース", race_date=tomorrow)
        db_session.add(race)
        await db_session.commit()

        response = await client.get("/api/races/upcoming")

        assert response.status_code == 200
        data = response.json()
        assert any(item["name"] == "未来レース" for item in data)

    @pytest.mark.asyncio
    async def test_search_races(self, client, test_race):
        """GET /api/races/search?name= searches by name."""
        response = await client.get("/api/races/search?name=有馬")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("有馬" in item["name"] for item in data)

    @pytest.mark.asyncio
    async def test_search_races_no_match(self, client, db_session):
        """GET /api/races/search returns empty for no match."""
        response = await client.get("/api/races/search?name=存在しないレース")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_get_races_by_date(self, client, test_race):
        """GET /api/races/by-date returns races in date range."""
        response = await client.get(
            "/api/races/by-date?start_date=2024-12-01&end_date=2024-12-31"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_races_by_date_invalid_range(self, client):
        """GET /api/races/by-date returns 400 for invalid range."""
        response = await client.get(
            "/api/races/by-date?start_date=2024-12-31&end_date=2024-12-01"
        )

        assert response.status_code == 400
        assert "start_date must be before end_date" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_race(self, client, db_session):
        """POST /api/races creates a new race."""
        race_data = {
            "name": "新規レース",
            "date": "2024-11-15",
            "venue": "東京",
            "course_type": "芝",
            "distance": 2400,
            "grade": "G1",
            "track_condition": "良",
            "weather": "晴",
            "purse": 30000,
        }

        response = await client.post("/api/races", json=race_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "新規レース"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_create_race_validation_error(self, client, db_session):
        """POST /api/races returns 422 for invalid data."""
        race_data = {
            "name": "",  # Empty name
            "date": "2024-11-15",
            "venue": "東京",
            "course_type": "芝",
            "distance": 100,  # Too short
            "grade": "G1",
        }

        response = await client.post("/api/races", json=race_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_race(self, client, test_race):
        """PUT /api/races/{id} updates a race."""
        update_data = {
            "name": "更新レース",
            "distance": 3000,
        }

        response = await client.put(f"/api/races/{test_race.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新レース"
        assert data["distance"] == 3000

    @pytest.mark.asyncio
    async def test_update_race_not_found(self, client, db_session):
        """PUT /api/races/{id} returns 404 for non-existent race."""
        response = await client.put("/api/races/99999", json={"name": "更新"})

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_race(self, client, test_race):
        """DELETE /api/races/{id} deletes a race."""
        response = await client.delete(f"/api/races/{test_race.id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(f"/api/races/{test_race.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_race_not_found(self, client, db_session):
        """DELETE /api/races/{id} returns 404 for non-existent race."""
        response = await client.delete("/api/races/99999")

        assert response.status_code == 404
