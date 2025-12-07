"""Race service."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Race
from app.repositories import EntryRepository, RaceRepository
from app.schemas import RaceCreate, RaceResponse, RaceUpdate


class RaceService:
    """Service for race operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.race_repo = RaceRepository(session)
        self.entry_repo = EntryRepository(session)

    async def get_race(self, race_id: int) -> RaceResponse | None:
        """Get a race by ID."""
        race = await self.race_repo.get(race_id)
        if not race:
            return None

        entries_count = await self.race_repo.get_entries_count(race_id)
        return self._to_response(race, entries_count)

    async def get_race_with_entries(self, race_id: int) -> Race | None:
        """Get a race with entries."""
        return await self.race_repo.get_with_entries(race_id)

    async def get_races(
        self,
        skip: int = 0,
        limit: int = 100,
        grade: str | None = None,
    ) -> tuple[list[RaceResponse], int]:
        """Get races with pagination."""
        filters = {}
        if grade:
            filters["grade"] = grade

        races = await self.race_repo.get_all(skip=skip, limit=limit, filters=filters)
        total = await self.race_repo.count(filters=filters)

        responses = []
        for race in races:
            entries_count = await self.race_repo.get_entries_count(race.id)
            responses.append(self._to_response(race, entries_count))

        return responses, total

    async def get_races_by_date_range(
        self,
        start_date: date,
        end_date: date,
        grade: str | None = None,
    ) -> list[RaceResponse]:
        """Get races within a date range."""
        races = await self.race_repo.get_by_date_range(start_date, end_date, grade)
        responses = []
        for race in races:
            entries_count = await self.race_repo.get_entries_count(race.id)
            responses.append(self._to_response(race, entries_count))
        return responses

    async def get_upcoming_races(self, limit: int = 10) -> list[RaceResponse]:
        """Get upcoming races."""
        races = await self.race_repo.get_upcoming_races(limit)
        responses = []
        for race in races:
            entries_count = await self.race_repo.get_entries_count(race.id)
            responses.append(self._to_response(race, entries_count))
        return responses

    async def create_race(self, data: RaceCreate) -> RaceResponse:
        """Create a new race."""
        race = await self.race_repo.create(data.model_dump())
        return self._to_response(race, 0)

    async def update_race(
        self, race_id: int, data: RaceUpdate
    ) -> RaceResponse | None:
        """Update a race."""
        race = await self.race_repo.update(
            race_id, data.model_dump(exclude_unset=True)
        )
        if not race:
            return None

        entries_count = await self.race_repo.get_entries_count(race_id)
        return self._to_response(race, entries_count)

    async def delete_race(self, race_id: int) -> bool:
        """Delete a race."""
        return await self.race_repo.delete(race_id)

    async def search_races(self, name: str, limit: int = 20) -> list[RaceResponse]:
        """Search races by name."""
        races = await self.race_repo.search_by_name(name, limit)
        responses = []
        for race in races:
            entries_count = await self.race_repo.get_entries_count(race.id)
            responses.append(self._to_response(race, entries_count))
        return responses

    def _to_response(self, race: Race, entries_count: int) -> RaceResponse:
        """Convert Race model to RaceResponse."""
        return RaceResponse(
            id=race.id,
            name=race.name,
            date=race.date,
            venue=race.venue,
            course_type=race.course_type,
            distance=race.distance,
            track_condition=race.track_condition,
            weather=race.weather,
            grade=race.grade,
            purse=race.purse,
            entries_count=entries_count,
            created_at=race.created_at,
            updated_at=race.updated_at,
        )
