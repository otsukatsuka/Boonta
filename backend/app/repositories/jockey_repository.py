"""Jockey repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Jockey
from app.repositories.base import BaseRepository


class JockeyRepository(BaseRepository[Jockey]):
    """Repository for Jockey model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Jockey, session)

    async def get_by_name(self, name: str) -> Jockey | None:
        """Get jockey by exact name."""
        result = await self.session.execute(
            select(Jockey).where(Jockey.name == name)
        )
        return result.scalar_one_or_none()

    async def search_by_name(self, name: str, limit: int = 20) -> list[Jockey]:
        """Search jockeys by name."""
        query = (
            select(Jockey)
            .where(Jockey.name.contains(name))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_or_create(self, name: str, **kwargs) -> tuple[Jockey, bool]:
        """Get existing jockey or create new one."""
        jockey = await self.get_by_name(name)
        if jockey:
            return jockey, False

        jockey = await self.create({"name": name, **kwargs})
        return jockey, True
