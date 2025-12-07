"""Horse repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Horse, RaceResult
from app.repositories.base import BaseRepository


class HorseRepository(BaseRepository[Horse]):
    """Repository for Horse model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Horse, session)

    async def get_by_name(self, name: str) -> Horse | None:
        """Get horse by exact name."""
        result = await self.session.execute(
            select(Horse).where(Horse.name == name)
        )
        return result.scalar_one_or_none()

    async def search_by_name(self, name: str, limit: int = 20) -> list[Horse]:
        """Search horses by name."""
        query = (
            select(Horse)
            .where(Horse.name.contains(name))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_results(self, horse_id: int) -> Horse | None:
        """Get horse with race results loaded."""
        result = await self.session.execute(
            select(Horse)
            .options(
                selectinload(Horse.results).selectinload(RaceResult.race),
                selectinload(Horse.results).selectinload(RaceResult.jockey),
            )
            .where(Horse.id == horse_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str, **kwargs) -> tuple[Horse, bool]:
        """Get existing horse or create new one."""
        horse = await self.get_by_name(name)
        if horse:
            return horse, False

        horse = await self.create({"name": name, **kwargs})
        return horse, True
