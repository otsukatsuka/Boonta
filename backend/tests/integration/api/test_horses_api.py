"""Tests for horses API endpoints."""

import pytest


class TestHorsesAPI:
    """Tests for /api/horses endpoints."""

    @pytest.mark.asyncio
    async def test_get_horses(self, client, test_horse):
        """GET /api/horses returns list of horses."""
        response = await client.get("/api/horses")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_horses_with_pagination(self, client, test_horses):
        """GET /api/horses respects skip and limit."""
        response = await client.get("/api/horses?skip=0&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_get_horse(self, client, test_horse):
        """GET /api/horses/{id} returns a horse."""
        response = await client.get(f"/api/horses/{test_horse.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_horse.id
        assert data["name"] == test_horse.name

    @pytest.mark.asyncio
    async def test_get_horse_not_found(self, client, db_session):
        """GET /api/horses/{id} returns 404 for non-existent horse."""
        response = await client.get("/api/horses/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Horse not found"

    @pytest.mark.asyncio
    async def test_search_horses(self, client, test_horses):
        """GET /api/horses/search?name= searches by name."""
        response = await client.get("/api/horses/search?name=イクイノックス")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("イクイノックス" in item["name"] for item in data)

    @pytest.mark.asyncio
    async def test_search_horses_partial_match(self, client, test_horses):
        """GET /api/horses/search matches partial names."""
        response = await client.get("/api/horses/search?name=ド")

        assert response.status_code == 200
        data = response.json()
        # Should match ドウデュース, ボルドグフーシュ, etc.
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_search_horses_no_match(self, client, db_session):
        """GET /api/horses/search returns empty for no match."""
        response = await client.get("/api/horses/search?name=存在しない馬")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_get_horse_results(self, client, test_race, test_horses, db_session):
        """GET /api/horses/{id}/results returns race results."""
        from app.models import RaceResult

        horse = test_horses[0]
        result = RaceResult(
            race_id=test_race.id,
            horse_id=horse.id,
            position=1,
            time=150.5,
            last_3f=33.5,
        )
        db_session.add(result)
        await db_session.commit()

        response = await client.get(f"/api/horses/{horse.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_get_horse_results_no_results(self, client, test_horse):
        """GET /api/horses/{id}/results returns empty for horse with no results."""
        response = await client.get(f"/api/horses/{test_horse.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_get_horse_results_not_found(self, client, db_session):
        """GET /api/horses/{id}/results returns 404 for non-existent horse."""
        response = await client.get("/api/horses/99999/results")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_horse(self, client, db_session):
        """POST /api/horses creates a new horse."""
        horse_data = {
            "name": "新馬",
            "age": 3,
            "sex": "牡",
            "trainer": "新調教師",
            "owner": "新オーナー",
        }

        response = await client.post("/api/horses", json=horse_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "新馬"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_update_horse(self, client, test_horse):
        """PUT /api/horses/{id} updates a horse."""
        update_data = {
            "age": 6,
        }

        response = await client.put(f"/api/horses/{test_horse.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["age"] == 6

    @pytest.mark.asyncio
    async def test_update_horse_not_found(self, client, db_session):
        """PUT /api/horses/{id} returns 404 for non-existent horse."""
        response = await client.put("/api/horses/99999", json={"age": 5})

        assert response.status_code == 404
