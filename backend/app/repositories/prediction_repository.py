"""Prediction repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Prediction
from app.repositories.base import BaseRepository


class PredictionRepository(BaseRepository[Prediction]):
    """Repository for Prediction model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Prediction, session)

    async def get_by_race(self, race_id: int) -> Prediction | None:
        """Get latest prediction for a race."""
        result = await self.session.execute(
            select(Prediction)
            .where(Prediction.race_id == race_id)
            .order_by(Prediction.predicted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history_by_race(
        self, race_id: int, limit: int = 10
    ) -> list[Prediction]:
        """Get prediction history for a race."""
        result = await self.session.execute(
            select(Prediction)
            .options(selectinload(Prediction.race))
            .where(Prediction.race_id == race_id)
            .order_by(Prediction.predicted_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_by_model_version(
        self, model_version: str, limit: int = 20
    ) -> list[Prediction]:
        """Get latest predictions by model version."""
        result = await self.session.execute(
            select(Prediction)
            .options(selectinload(Prediction.race))
            .where(Prediction.model_version == model_version)
            .order_by(Prediction.predicted_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
