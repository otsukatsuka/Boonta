"""Race entry repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import RaceEntry
from app.repositories.base import BaseRepository


class EntryRepository(BaseRepository[RaceEntry]):
    """Repository for RaceEntry model."""

    def __init__(self, session: AsyncSession):
        super().__init__(RaceEntry, session)

    async def get_by_race(self, race_id: int) -> list[RaceEntry]:
        """Get all entries for a race."""
        result = await self.session.execute(
            select(RaceEntry)
            .options(
                selectinload(RaceEntry.horse),
                selectinload(RaceEntry.jockey),
            )
            .where(RaceEntry.race_id == race_id)
            .order_by(RaceEntry.horse_number)
        )
        return list(result.scalars().all())

    async def get_by_race_and_horse(
        self, race_id: int, horse_id: int
    ) -> RaceEntry | None:
        """Get entry by race and horse."""
        result = await self.session.execute(
            select(RaceEntry).where(
                RaceEntry.race_id == race_id,
                RaceEntry.horse_id == horse_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_with_relations(self, entry_id: int) -> RaceEntry | None:
        """Get entry with horse and jockey loaded."""
        result = await self.session.execute(
            select(RaceEntry)
            .options(
                selectinload(RaceEntry.horse),
                selectinload(RaceEntry.jockey),
                selectinload(RaceEntry.race),
            )
            .where(RaceEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def update_workout(
        self,
        entry_id: int,
        workout_time: str | None = None,
        workout_evaluation: str | None = None,
        workout_course: str | None = None,
        workout_memo: str | None = None,
    ) -> RaceEntry | None:
        """Update workout information."""
        data = {}
        if workout_time is not None:
            data["workout_time"] = workout_time
        if workout_evaluation is not None:
            data["workout_evaluation"] = workout_evaluation
        if workout_course is not None:
            data["workout_course"] = workout_course
        if workout_memo is not None:
            data["workout_memo"] = workout_memo

        return await self.update(entry_id, data)

    async def update_comment(
        self, entry_id: int, trainer_comment: str | None
    ) -> RaceEntry | None:
        """Update trainer comment."""
        return await self.update(entry_id, {"trainer_comment": trainer_comment})
