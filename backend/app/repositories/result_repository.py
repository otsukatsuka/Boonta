"""Race result repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Race, RaceResult
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

    async def get_by_horse_with_conditions(
        self,
        horse_id: int,
        distance: int | None = None,
        venue: str | None = None,
        track_condition: str | None = None,
        limit: int = 20,
    ) -> list[RaceResult]:
        """Get results for a horse with optional condition filters.

        Args:
            horse_id: Horse ID
            distance: Target distance (will match ±200m range)
            venue: Target venue name
            track_condition: Target track condition (良/稍重/重/不良)
            limit: Maximum number of results
        """
        query = (
            select(RaceResult)
            .join(Race, RaceResult.race_id == Race.id)
            .options(
                selectinload(RaceResult.race),
                selectinload(RaceResult.jockey),
            )
            .where(RaceResult.horse_id == horse_id)
        )

        if distance is not None:
            # Match within ±200m range
            query = query.where(
                Race.distance >= distance - 200,
                Race.distance <= distance + 200,
            )

        if venue is not None:
            query = query.where(Race.venue == venue)

        if track_condition is not None:
            query = query.where(Race.track_condition == track_condition)

        query = query.order_by(RaceResult.id.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
