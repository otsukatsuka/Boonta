"""Tests for entries API endpoints."""

import pytest


class TestEntriesAPI:
    """Tests for /api/entries endpoints."""

    @pytest.mark.asyncio
    async def test_get_race_entries(self, client, test_race, test_entries):
        """GET /api/races/{race_id}/entries returns entries."""
        response = await client.get(f"/api/races/{test_race.id}/entries")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == len(test_entries)

    @pytest.mark.asyncio
    async def test_get_race_entries_includes_horse_jockey(
        self, client, test_race, test_entries
    ):
        """Entries include horse and jockey names."""
        response = await client.get(f"/api/races/{test_race.id}/entries")

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert "horse_name" in item
            assert item["horse_name"] is not None

    @pytest.mark.asyncio
    async def test_get_race_entries_race_not_found(self, client, db_session):
        """GET /api/races/{race_id}/entries returns 404 for non-existent race."""
        response = await client.get("/api/races/99999/entries")

        assert response.status_code == 404
        assert response.json()["detail"] == "Race not found"

    @pytest.mark.asyncio
    async def test_get_race_entries_empty(self, client, test_race):
        """GET /api/races/{race_id}/entries returns empty for race with no entries."""
        response = await client.get(f"/api/races/{test_race.id}/entries")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_add_race_entry(self, client, test_race, test_horse, test_jockey):
        """POST /api/races/{race_id}/entries adds an entry."""
        entry_data = {
            "race_id": test_race.id,
            "horse_id": test_horse.id,
            "jockey_id": test_jockey.id,
            "horse_number": 1,
            "post_position": 1,
            "weight": 57.0,
            "horse_weight": 480,
            "horse_weight_diff": 0,
            "odds": 5.0,
            "popularity": 1,
            "running_style": "FRONT",
        }

        response = await client.post(
            f"/api/races/{test_race.id}/entries", json=entry_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["horse_id"] == test_horse.id
        assert data["horse_name"] == test_horse.name

    @pytest.mark.asyncio
    async def test_add_race_entry_race_not_found(
        self, client, db_session, test_horse
    ):
        """POST /api/races/{race_id}/entries returns 404 for non-existent race."""
        entry_data = {
            "race_id": 99999,
            "horse_id": test_horse.id,
            "horse_number": 1,
        }

        response = await client.post("/api/races/99999/entries", json=entry_data)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_race_entry_race_id_mismatch(
        self, client, test_race, test_horse
    ):
        """POST with mismatched race_id returns 400."""
        entry_data = {
            "race_id": 99999,  # Different from URL
            "horse_id": test_horse.id,
            "horse_number": 1,
        }

        response = await client.post(
            f"/api/races/{test_race.id}/entries", json=entry_data
        )

        assert response.status_code == 400
        assert "race_id in body must match URL" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_race_entry_duplicate(
        self, client, test_race, test_entries
    ):
        """POST duplicate entry returns 400."""
        # Try to add the same horse again
        entry = test_entries[0]
        entry_data = {
            "race_id": test_race.id,
            "horse_id": entry.horse_id,
            "jockey_id": entry.jockey_id,
            "horse_number": 17,  # Valid range 1-18
            "post_position": 1,
            "weight": 57.0,
            "horse_weight": 480,
            "horse_weight_diff": 0,
            "odds": 10.0,
            "popularity": 5,
            "running_style": "FRONT",
        }

        response = await client.post(
            f"/api/races/{test_race.id}/entries", json=entry_data
        )

        assert response.status_code == 400
        assert "Entry already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_entry(self, client, test_race, test_entries):
        """PUT /api/entries/{entry_id} updates an entry."""
        entry = test_entries[0]
        update_data = {
            "odds": 10.0,
            "popularity": 3,
        }

        response = await client.put(f"/api/entries/{entry.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["odds"] == 10.0
        assert data["popularity"] == 3

    @pytest.mark.asyncio
    async def test_update_entry_not_found(self, client, db_session):
        """PUT /api/entries/{entry_id} returns 404 for non-existent entry."""
        response = await client.put("/api/entries/99999", json={"odds": 5.0})

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_entry_workout(self, client, test_race, test_entries):
        """PUT /api/entries/{entry_id}/workout updates workout info."""
        entry = test_entries[0]
        workout_data = {
            "workout_time": "1:12.5",
            "workout_evaluation": "A",
            "workout_course": "美浦坂路",
            "workout_memo": "好調子",
        }

        response = await client.put(
            f"/api/entries/{entry.id}/workout", json=workout_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workout_time"] == "1:12.5"
        assert data["workout_evaluation"] == "A"

    @pytest.mark.asyncio
    async def test_update_entry_workout_not_found(self, client, db_session):
        """PUT /api/entries/{entry_id}/workout returns 404."""
        response = await client.put(
            "/api/entries/99999/workout",
            json={"workout_evaluation": "A"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_entry_comment(self, client, test_race, test_entries):
        """PUT /api/entries/{entry_id}/comment updates trainer comment."""
        entry = test_entries[0]
        comment_data = {
            "trainer_comment": "調子良好、勝負気配",
        }

        response = await client.put(
            f"/api/entries/{entry.id}/comment", json=comment_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trainer_comment"] == "調子良好、勝負気配"

    @pytest.mark.asyncio
    async def test_update_entry_comment_not_found(self, client, db_session):
        """PUT /api/entries/{entry_id}/comment returns 404."""
        response = await client.put(
            "/api/entries/99999/comment",
            json={"trainer_comment": "コメント"},
        )

        assert response.status_code == 404
