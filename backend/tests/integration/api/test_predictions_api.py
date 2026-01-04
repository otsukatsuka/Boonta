"""Tests for predictions API endpoints."""

from datetime import datetime, timezone

import pytest

from app.models import Prediction


class TestPredictionsAPI:
    """Tests for /api/predictions endpoints."""

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
                    {
                        "rank": 1,
                        "horse_id": 1,
                        "horse_name": "テスト馬1",
                        "horse_number": 1,
                        "score": 0.8,
                        "win_probability": 0.3,
                        "place_probability": 0.6,
                        "popularity": 1,
                        "odds": 3.5,
                        "is_dark_horse": False,
                    },
                    {
                        "rank": 2,
                        "horse_id": 2,
                        "horse_name": "テスト馬2",
                        "horse_number": 2,
                        "score": 0.6,
                        "win_probability": 0.2,
                        "place_probability": 0.5,
                        "popularity": 2,
                        "odds": 5.0,
                        "is_dark_horse": False,
                    },
                ],
                "pace_prediction": {
                    "type": "middle",
                    "confidence": 0.7,
                    "reason": "テストペース予測",
                    "advantageous_styles": ["FRONT", "STALKER"],
                    "escape_count": 2,
                    "front_count": 3,
                },
                "recommended_bets": {
                    "trio": {"type": "2軸流し", "pivots": [1, 2], "with_": [3, 4, 5]},
                    "trifecta_multi": None,
                    "total_investment": 1000,
                    "note": "テスト馬券",
                },
            },
            confidence_score=confidence_score,
            reasoning="テスト予測根拠",
        )
        db_session.add(prediction)
        await db_session.commit()
        await db_session.refresh(prediction)
        return prediction

    @pytest.mark.asyncio
    async def test_get_prediction(self, client, db_session, test_race):
        """GET /api/predictions/{race_id} returns prediction."""
        prediction = await self._create_prediction(db_session, test_race.id)

        response = await client.get(f"/api/predictions/{test_race.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["race_id"] == test_race.id
        assert "rankings" in data
        assert "recommended_bets" in data
        assert "confidence_score" in data

    @pytest.mark.asyncio
    async def test_get_prediction_not_found(self, client, test_race):
        """GET /api/predictions/{race_id} returns 404 when no prediction."""
        response = await client.get(f"/api/predictions/{test_race.id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Prediction not found"

    @pytest.mark.asyncio
    async def test_get_prediction_nonexistent_race(self, client, db_session):
        """GET /api/predictions/{race_id} returns 404 for non-existent race."""
        response = await client.get("/api/predictions/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_prediction_history(self, client, db_session, test_race):
        """GET /api/predictions/{race_id}/history returns prediction history."""
        # Create multiple predictions
        for i in range(3):
            await self._create_prediction(
                db_session,
                test_race.id,
                predicted_at=datetime(2024, 1, 1, 10 + i, 0, tzinfo=timezone.utc),
                model_version=f"v1.{i}",
            )

        response = await client.get(f"/api/predictions/{test_race.id}/history")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_get_prediction_history_empty(self, client, test_race):
        """GET /api/predictions/{race_id}/history returns empty when no predictions."""
        response = await client.get(f"/api/predictions/{test_race.id}/history")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_prediction_history_limit(self, client, db_session, test_race):
        """GET /api/predictions/{race_id}/history respects limit."""
        # Create multiple predictions
        for i in range(5):
            await self._create_prediction(
                db_session,
                test_race.id,
                predicted_at=datetime(2024, 1, 1, 10 + i, 0, tzinfo=timezone.utc),
            )

        response = await client.get(f"/api/predictions/{test_race.id}/history?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_create_prediction(self, client, test_race, test_entries):
        """POST /api/predictions/{race_id} creates a prediction."""
        response = await client.post(f"/api/predictions/{test_race.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["race_id"] == test_race.id
        assert "rankings" in data
        assert "recommended_bets" in data

    @pytest.mark.asyncio
    async def test_create_prediction_race_not_found(self, client, db_session):
        """POST /api/predictions/{race_id} returns 404 for non-existent race."""
        response = await client.post("/api/predictions/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_prediction_no_entries(self, client, test_race):
        """POST /api/predictions/{race_id} returns 404 for race with no entries."""
        response = await client.post(f"/api/predictions/{test_race.id}")

        assert response.status_code == 404
        assert "no entries" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_simulation(self, client, test_race, test_entries):
        """GET /api/predictions/{race_id}/simulation returns simulation."""
        response = await client.get(f"/api/predictions/{test_race.id}/simulation")

        assert response.status_code == 200
        data = response.json()
        assert data["race_id"] == test_race.id
        assert "corner_positions" in data
        assert "start_formation" in data
        assert "scenarios" in data
        assert "predicted_pace" in data

    @pytest.mark.asyncio
    async def test_get_simulation_not_found(self, client, db_session):
        """GET /api/predictions/{race_id}/simulation returns 404 for non-existent race."""
        response = await client.get("/api/predictions/99999/simulation")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_simulation_no_entries(self, client, test_race):
        """GET /api/predictions/{race_id}/simulation returns 404 for race with no entries."""
        response = await client.get(f"/api/predictions/{test_race.id}/simulation")

        assert response.status_code == 404
        assert "no entries" in response.json()["detail"]
