"""Race result repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import RaceResult
from app.repositories.base import BaseRepository


class ResultRepository(BaseRepository[RaceResult]):
    """Repository for RaceResult model."""

    def __init__(self, session: AsyncSession):
        super().__init__(RaceResult, session)

    async def get_by_race(self, race_id: int) -> list[RaceResult]:
        """Get all results for a race."""
        result = await self.session.execute(
            select(RaceResult)
            .options(
                selectinload(RaceResult.horse),
                selectinload(RaceResult.jockey),
            )
            .where(RaceResult.race_id == race_id)
            .order_by(RaceResult.position)
        )
        return list(result.scalars().all())

    async def get_by_horse(
        self, horse_id: int, limit: int = 10
    ) -> list[RaceResult]:
        """Get results for a horse."""
        result = await self.session.execute(
            select(RaceResult)
            .options(
                selectinload(RaceResult.race),
                selectinload(RaceResult.jockey),
            )
            .where(RaceResult.horse_id == horse_id)
            .order_by(RaceResult.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_jockey(
        self, jockey_id: int, limit: int = 50
    ) -> list[RaceResult]:
        """Get results for a jockey."""
        result = await self.session.execute(
            select(RaceResult)
            .options(
                selectinload(RaceResult.race),
                selectinload(RaceResult.horse),
            )
            .where(RaceResult.jockey_id == jockey_id)
            .order_by(RaceResult.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_race_and_horse(
        self, race_id: int, horse_id: int
    ) -> RaceResult | None:
        """Get result by race and horse."""
        result = await self.session.execute(
            select(RaceResult).where(
                RaceResult.race_id == race_id,
                RaceResult.horse_id == horse_id,
            )
        )
        return result.scalar_one_or_none()
