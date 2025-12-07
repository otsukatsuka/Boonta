"""Race repository."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Race, RaceEntry
from app.repositories.base import BaseRepository


class RaceRepository(BaseRepository[Race]):
    """Repository for Race model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Race, session)

    async def get_with_entries(self, race_id: int) -> Race | None:
        """Get race with entries loaded."""
        result = await self.session.execute(
            select(Race)
            .options(
                selectinload(Race.entries).selectinload(RaceEntry.horse),
                selectinload(Race.entries).selectinload(RaceEntry.jockey),
            )
            .where(Race.id == race_id)
        )
        return result.scalar_one_or_none()

    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        grade: str | None = None,
    ) -> list[Race]:
        """Get races within a date range."""
        query = select(Race).where(
            Race.date >= start_date,
            Race.date <= end_date,
        )

        if grade:
            query = query.where(Race.grade == grade)

        query = query.order_by(Race.date)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_upcoming_races(self, limit: int = 10) -> list[Race]:
        """Get upcoming races."""
        today = date.today()
        query = (
            select(Race)
            .where(Race.date >= today)
            .order_by(Race.date)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_entries_count(self, race_id: int) -> int:
        """Get the number of entries for a race."""
        result = await self.session.execute(
            select(func.count()).select_from(RaceEntry).where(RaceEntry.race_id == race_id)
        )
        return result.scalar_one()

    async def search_by_name(self, name: str, limit: int = 20) -> list[Race]:
        """Search races by name."""
        query = (
            select(Race)
            .where(Race.name.contains(name))
            .order_by(Race.date.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
