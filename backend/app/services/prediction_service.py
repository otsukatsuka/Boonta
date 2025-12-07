"""Prediction service."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Prediction, RaceEntry
from app.repositories import EntryRepository, PredictionRepository, RaceRepository
from app.schemas import (
    BetRecommendation,
    HorsePrediction,
    PacePrediction,
    PredictionResponse,
)

settings = get_settings()


class PredictionService:
    """Service for prediction operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.race_repo = RaceRepository(session)
        self.entry_repo = EntryRepository(session)
        self.prediction_repo = PredictionRepository(session)

    async def get_prediction(self, race_id: int) -> PredictionResponse | None:
        """Get latest prediction for a race."""
        prediction = await self.prediction_repo.get_by_race(race_id)
        if not prediction:
            return None
        return self._to_response(prediction)

    async def get_prediction_history(
        self, race_id: int, limit: int = 10
    ) -> list[Prediction]:
        """Get prediction history for a race."""
        return await self.prediction_repo.get_history_by_race(race_id, limit)

    async def create_prediction(self, race_id: int) -> PredictionResponse | None:
        """Create a new prediction for a race."""
        race = await self.race_repo.get_with_entries(race_id)
        if not race:
            return None

        entries = await self.entry_repo.get_by_race(race_id)
        if not entries:
            return None

        # Generate pace prediction
        pace_prediction = self._predict_pace(entries)

        # Generate horse rankings (placeholder - will be replaced by ML model)
        rankings = self._generate_rankings(entries, pace_prediction)

        # Generate bet recommendations
        recommended_bets = self._generate_bets(rankings, pace_prediction)

        # Calculate overall confidence
        confidence_score = self._calculate_confidence(rankings, pace_prediction)

        # Generate reasoning
        reasoning = self._generate_reasoning(rankings, pace_prediction)

        # Create prediction data
        prediction_data = {
            "rankings": [r.model_dump() for r in rankings],
            "pace_prediction": pace_prediction.model_dump() if pace_prediction else None,
            "recommended_bets": recommended_bets.model_dump() if recommended_bets else None,
        }

        # Save prediction
        prediction = await self.prediction_repo.create({
            "race_id": race_id,
            "model_version": settings.model_version,
            "predicted_at": datetime.now(timezone.utc),
            "prediction_data": prediction_data,
            "confidence_score": confidence_score,
            "reasoning": reasoning,
        })

        return self._to_response(prediction)

    def _predict_pace(self, entries: list[RaceEntry]) -> PacePrediction:
        """Predict race pace based on running styles."""
        escape_count = sum(
            1 for e in entries if e.running_style == "ESCAPE"
        )
        front_count = sum(
            1 for e in entries if e.running_style == "FRONT"
        )

        if escape_count >= 2:
            pace_type = "high"
            advantage = ["STALKER", "CLOSER"]
            reason = f"逃げ馬が{escape_count}頭で競り合いが予想される"
        elif escape_count <= 1 and front_count <= 3:
            pace_type = "slow"
            advantage = ["ESCAPE", "FRONT"]
            reason = "逃げ馬が少なく、スローペースが予想される"
        else:
            pace_type = "middle"
            advantage = ["FRONT", "STALKER"]
            reason = "平均的なペースが予想される"

        confidence = 0.7 if escape_count > 0 else 0.5

        return PacePrediction(
            type=pace_type,
            confidence=confidence,
            reason=reason,
            advantageous_styles=advantage,
            escape_count=escape_count,
            front_count=front_count,
        )

    def _generate_rankings(
        self,
        entries: list[RaceEntry],
        pace: PacePrediction,
    ) -> list[HorsePrediction]:
        """Generate horse rankings (placeholder implementation)."""
        rankings = []

        for i, entry in enumerate(entries):
            # Simple scoring based on odds and pace advantage
            base_score = 1.0 / (entry.odds or 10.0) if entry.odds else 0.1

            # Boost score if running style matches pace advantage
            if entry.running_style in pace.advantageous_styles:
                base_score *= 1.2

            # Check if dark horse
            is_dark_horse = (
                entry.popularity is not None
                and entry.popularity >= 6
                and base_score >= 0.05
            )

            rankings.append(HorsePrediction(
                rank=i + 1,
                horse_id=entry.horse_id,
                horse_name=entry.horse.name if entry.horse else "Unknown",
                horse_number=entry.horse_number or i + 1,
                score=min(base_score, 1.0),
                win_probability=min(base_score * 0.5, 0.5),
                place_probability=min(base_score * 1.5, 0.8),
                popularity=entry.popularity,
                odds=entry.odds,
                is_dark_horse=is_dark_horse,
                dark_horse_reason="人気薄だが好走の可能性あり" if is_dark_horse else None,
            ))

        # Sort by score and update ranks
        rankings.sort(key=lambda x: x.score, reverse=True)
        for i, r in enumerate(rankings):
            r.rank = i + 1

        return rankings

    def _generate_bets(
        self,
        rankings: list[HorsePrediction],
        pace: PacePrediction,
    ) -> BetRecommendation:
        """Generate bet recommendations."""
        if len(rankings) < 3:
            return BetRecommendation(total_investment=0)

        top_horses = [r.horse_number for r in rankings[:2]]
        counter_horses = [r.horse_number for r in rankings[2:6]]
        dark_horses = [r.horse_number for r in rankings if r.is_dark_horse][:2]

        all_horses = top_horses + counter_horses[:2] + dark_horses

        trifecta = {
            "type": "formation",
            "first": top_horses,
            "second": top_horses + counter_horses[:2],
            "third": all_horses,
            "combinations": len(top_horses) * len(top_horses + counter_horses[:2]) * len(all_horses),
            "amount_per_ticket": 100,
        }

        trio = {
            "type": "box",
            "horses": all_horses[:5],
            "combinations": 10,
            "amount_per_ticket": 300,
        }

        exacta = None
        if rankings[0].score > 0.3:
            exacta = {
                "type": "first_to_others",
                "first": rankings[0].horse_number,
                "second": counter_horses[:3],
                "combinations": 3,
                "amount_per_ticket": 500,
            }

        wide = None
        if dark_horses:
            wide = {
                "pairs": [[dark_horses[0], top_horses[0]]],
                "note": f"穴馬{dark_horses[0]}番絡み",
                "amount_per_ticket": 200,
            }

        total = (
            trifecta["combinations"] * trifecta["amount_per_ticket"]
            + trio["combinations"] * trio["amount_per_ticket"]
            + (exacta["combinations"] * exacta["amount_per_ticket"] if exacta else 0)
            + (len(wide["pairs"]) * wide["amount_per_ticket"] if wide else 0)
        )

        return BetRecommendation(
            trifecta=trifecta,
            trio=trio,
            exacta=exacta,
            wide=wide,
            total_investment=total,
            note=f"軸: {top_horses[0]},{top_horses[1]}番",
        )

    def _calculate_confidence(
        self,
        rankings: list[HorsePrediction],
        pace: PacePrediction,
    ) -> float:
        """Calculate overall prediction confidence."""
        if not rankings:
            return 0.0

        # Base confidence from pace prediction
        confidence = pace.confidence * 0.3

        # Add confidence from top horse score difference
        if len(rankings) >= 2:
            score_diff = rankings[0].score - rankings[1].score
            confidence += min(score_diff * 2, 0.3)

        # Add confidence from odds spread
        if rankings[0].odds and rankings[-1].odds:
            odds_ratio = rankings[-1].odds / rankings[0].odds
            confidence += min(odds_ratio / 100, 0.2)

        return min(confidence + 0.2, 1.0)

    def _generate_reasoning(
        self,
        rankings: list[HorsePrediction],
        pace: PacePrediction,
    ) -> str:
        """Generate prediction reasoning text."""
        if not rankings:
            return "データ不足のため予測できません。"

        top = rankings[0]
        reasoning_parts = [
            f"{pace.type}ペース想定。",
            f"{pace.advantageous_styles[0]}脚質が有利。",
            f"{top.horse_number}番{top.horse_name}が本命。",
        ]

        dark_horses = [r for r in rankings if r.is_dark_horse]
        if dark_horses:
            dh = dark_horses[0]
            reasoning_parts.append(
                f"穴馬として{dh.horse_number}番に注目。"
            )

        return " ".join(reasoning_parts)

    def _to_response(self, prediction: Prediction) -> PredictionResponse:
        """Convert Prediction model to PredictionResponse."""
        data = prediction.prediction_data

        rankings = [
            HorsePrediction(**r) for r in data.get("rankings", [])
        ]

        pace_data = data.get("pace_prediction")
        pace_prediction = PacePrediction(**pace_data) if pace_data else None

        bets_data = data.get("recommended_bets")
        recommended_bets = BetRecommendation(**bets_data) if bets_data else None

        return PredictionResponse(
            race_id=prediction.race_id,
            model_version=prediction.model_version,
            predicted_at=prediction.predicted_at,
            rankings=rankings,
            pace_prediction=pace_prediction,
            recommended_bets=recommended_bets,
            confidence_score=prediction.confidence_score,
            reasoning=prediction.reasoning,
        )
