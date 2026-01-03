"""Data fetch API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.fetchers.netkeiba import NetkeibaFetcher
from app.repositories import EntryRepository, HorseRepository, JockeyRepository, RaceRepository

router = APIRouter(prefix="/fetch", tags=["fetch"])


class RegisterRaceRequest(BaseModel):
    """Request to register a new race from netkeiba."""

    netkeiba_race_id: str = Field(..., description="netkeiba race ID (e.g., 202606010111)")
    fetch_odds: bool = Field(True, description="Also fetch current odds")
    fetch_running_styles: bool = Field(False, description="Also fetch running styles (takes ~30s)")


class RegisterRaceResponse(BaseModel):
    """Response from race registration."""

    success: bool
    message: str
    race_id: int | None = None
    race_name: str | None = None
    entries_count: int = 0
    odds_updated: int = 0


@router.post("/register", response_model=RegisterRaceResponse)
async def register_race_from_netkeiba(
    request: RegisterRaceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new race from netkeiba ID.

    This endpoint:
    1. Fetches race information
    2. Creates the race in DB
    3. Fetches and creates all entries (horses, jockeys)
    4. Optionally fetches current odds
    5. Optionally fetches running styles
    """
    async with NetkeibaFetcher() as fetcher:
        # 1. Fetch race info
        race_info = await fetcher.fetch_race_info(request.netkeiba_race_id)
        if not race_info:
            raise HTTPException(
                status_code=404,
                detail=f"Race not found on netkeiba: {request.netkeiba_race_id}",
            )

        race_repo = RaceRepository(db)
        horse_repo = HorseRepository(db)
        jockey_repo = JockeyRepository(db)
        entry_repo = EntryRepository(db)

        # 2. Create race
        # Parse date string to date object
        race_date = datetime.strptime(race_info.date, "%Y-%m-%d").date()

        race = await race_repo.create({
            "name": race_info.name,
            "date": race_date,
            "venue": race_info.venue,
            "course_type": race_info.course_type,
            "distance": race_info.distance,
            "grade": race_info.grade,
            "track_condition": race_info.track_condition,
            "weather": race_info.weather,
            "purse": race_info.purse,
        })

        # 3. Fetch entries
        entries_info = await fetcher.fetch_entries(request.netkeiba_race_id)
        if not entries_info:
            return RegisterRaceResponse(
                success=True,
                message=f"Race '{race_info.name}' created but no entries found",
                race_id=race.id,
                race_name=race.name,
                entries_count=0,
            )

        # 4. Create entries
        for entry_info in entries_info:
            horse, _ = await horse_repo.get_or_create(
                name=entry_info.horse_name,
                trainer=entry_info.trainer,
            )
            jockey, _ = await jockey_repo.get_or_create(
                name=entry_info.jockey_name,
            )

            await entry_repo.create({
                "race_id": race.id,
                "horse_id": horse.id,
                "jockey_id": jockey.id,
                "horse_number": entry_info.horse_number,
                "post_position": entry_info.post_position,
                "weight": entry_info.weight,
                "odds": entry_info.odds,
                "popularity": entry_info.popularity,
                "horse_weight": entry_info.horse_weight,
                "horse_weight_diff": entry_info.horse_weight_diff,
            })

        odds_updated = 0

        # 5. Optionally fetch odds
        if request.fetch_odds:
            odds_list = await fetcher.fetch_shutuba_odds(request.netkeiba_race_id)
            if odds_list:
                entries = await entry_repo.get_by_race(race.id)
                for entry in entries:
                    odds_info = next(
                        (o for o in odds_list if o.horse_number == entry.horse_number),
                        None
                    )
                    if odds_info:
                        update_data = {}
                        if odds_info.odds is not None:
                            update_data["odds"] = odds_info.odds
                        if odds_info.popularity is not None:
                            update_data["popularity"] = odds_info.popularity
                        if update_data:
                            await entry_repo.update(entry.id, update_data)
                            odds_updated += 1

        # 6. Optionally fetch running styles
        if request.fetch_running_styles:
            style_list = await fetcher.fetch_running_styles(request.netkeiba_race_id)
            if style_list:
                entries = await entry_repo.get_by_race(race.id)
                for entry in entries:
                    style_info = next(
                        (s for s in style_list if s.horse_number == entry.horse_number),
                        None
                    )
                    if style_info and style_info.running_style:
                        await entry_repo.update(entry.id, {
                            "running_style": style_info.running_style,
                        })

        return RegisterRaceResponse(
            success=True,
            message=f"Race '{race_info.name}' registered successfully",
            race_id=race.id,
            race_name=race.name,
            entries_count=len(entries_info),
            odds_updated=odds_updated,
        )


class FetchRaceRequest(BaseModel):
    """Request to fetch race data."""

    race_id: str  # netkeiba race ID (e.g., "202405020811")


class FetchEntriesRequest(BaseModel):
    """Request to fetch entries."""

    netkeiba_race_id: str  # netkeiba race ID


class FetchResponse(BaseModel):
    """Response from fetch operation."""

    success: bool
    message: str
    data: dict | None = None


@router.post("/race", response_model=FetchResponse)
async def fetch_race(
    request: FetchRaceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetch race information from netkeiba and save to DB."""
    async with NetkeibaFetcher() as fetcher:
        race_info = await fetcher.fetch_race_info(request.race_id)

        if not race_info:
            raise HTTPException(
                status_code=404,
                detail=f"Race not found: {request.race_id}",
            )

        race_repo = RaceRepository(db)

        # Parse date string to date object
        race_date = datetime.strptime(race_info.date, "%Y-%m-%d").date()

        # Create race
        race = await race_repo.create({
            "name": race_info.name,
            "date": race_date,
            "venue": race_info.venue,
            "course_type": race_info.course_type,
            "distance": race_info.distance,
            "grade": race_info.grade,
            "track_condition": race_info.track_condition,
            "weather": race_info.weather,
            "purse": race_info.purse,
        })

        return FetchResponse(
            success=True,
            message=f"Race '{race_info.name}' created",
            data={"race_id": race.id, "name": race.name},
        )


@router.post("/entries/{race_id}", response_model=FetchResponse)
async def fetch_entries(
    race_id: int,
    request: FetchEntriesRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetch entry information from netkeiba and save to DB."""
    race_repo = RaceRepository(db)
    race = await race_repo.get(race_id)

    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    async with NetkeibaFetcher() as fetcher:
        entries_info = await fetcher.fetch_entries(request.netkeiba_race_id)

        if not entries_info:
            raise HTTPException(
                status_code=404,
                detail="No entries found",
            )

        horse_repo = HorseRepository(db)
        jockey_repo = JockeyRepository(db)
        entry_repo = EntryRepository(db)

        created_count = 0
        updated_count = 0

        for entry_info in entries_info:
            # Get or create horse
            horse, _ = await horse_repo.get_or_create(
                name=entry_info.horse_name,
                trainer=entry_info.trainer,
            )

            # Get or create jockey
            jockey, _ = await jockey_repo.get_or_create(
                name=entry_info.jockey_name,
            )

            # Check if entry already exists
            existing = await entry_repo.get_by_race_and_horse(race_id, horse.id)
            if existing:
                # Update odds and popularity if available from shutuba page
                if entry_info.odds is not None or entry_info.popularity is not None:
                    update_data = {}
                    if entry_info.odds is not None:
                        update_data["odds"] = entry_info.odds
                    if entry_info.popularity is not None:
                        update_data["popularity"] = entry_info.popularity
                    if update_data:
                        await entry_repo.update(existing.id, update_data)
                        updated_count += 1
                continue

            # Create entry
            await entry_repo.create({
                "race_id": race_id,
                "horse_id": horse.id,
                "jockey_id": jockey.id,
                "horse_number": entry_info.horse_number,
                "post_position": entry_info.post_position,
                "weight": entry_info.weight,
                "odds": entry_info.odds,
                "popularity": entry_info.popularity,
                "horse_weight": entry_info.horse_weight,
                "horse_weight_diff": entry_info.horse_weight_diff,
            })
            created_count += 1

        return FetchResponse(
            success=True,
            message=f"Created {created_count} entries, updated {updated_count} odds",
            data={"created": created_count, "updated": updated_count, "total": len(entries_info)},
        )


@router.post("/results/{horse_id}", response_model=FetchResponse)
async def fetch_horse_results(
    horse_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch horse results from external source."""
    # TODO: Implement result fetching and saving
    raise HTTPException(
        status_code=501,
        detail="Horse results fetching not yet implemented",
    )


class FetchOddsRequest(BaseModel):
    """Request to fetch odds from result page."""

    netkeiba_race_id: str  # netkeiba race ID


class FetchShutubaOddsRequest(BaseModel):
    """Request to fetch odds from shutuba (pre-race) page."""

    netkeiba_race_id: str  # netkeiba race ID


@router.post("/shutuba-odds/{race_id}", response_model=FetchResponse)
async def fetch_shutuba_odds(
    race_id: int,
    request: FetchShutubaOddsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetch odds and popularity from netkeiba shutuba page and update entries."""
    race_repo = RaceRepository(db)
    race = await race_repo.get(race_id)

    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    async with NetkeibaFetcher() as fetcher:
        odds_list = await fetcher.fetch_shutuba_odds(request.netkeiba_race_id)

        if not odds_list:
            raise HTTPException(
                status_code=404,
                detail="No odds data found. Check the netkeiba race ID.",
            )

        entry_repo = EntryRepository(db)
        entries = await entry_repo.get_by_race(race_id)

        updated_count = 0
        matched_count = 0
        for entry in entries:
            # Find matching odds info by horse number
            odds_info = next(
                (o for o in odds_list if o.horse_number == entry.horse_number),
                None
            )
            if odds_info:
                matched_count += 1
                update_data = {}
                if odds_info.odds is not None:
                    update_data["odds"] = odds_info.odds
                if odds_info.popularity is not None:
                    update_data["popularity"] = odds_info.popularity

                if update_data:
                    await entry_repo.update(entry.id, update_data)
                    updated_count += 1

        return FetchResponse(
            success=True,
            message=f"Updated {updated_count} entries with odds/popularity",
            data={
                "updated": updated_count,
                "matched": matched_count,
                "total_fetched": len(odds_list),
                "total_entries": len(entries),
            },
        )


class FetchRunningStylesRequest(BaseModel):
    """Request to fetch running styles from horse past results."""

    netkeiba_race_id: str  # netkeiba race ID


@router.post("/running-styles/{race_id}", response_model=FetchResponse)
async def fetch_running_styles(
    race_id: int,
    request: FetchRunningStylesRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetch running styles from netkeiba horse pages and update entries."""
    race_repo = RaceRepository(db)
    race = await race_repo.get(race_id)

    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    async with NetkeibaFetcher() as fetcher:
        style_list = await fetcher.fetch_running_styles(request.netkeiba_race_id)

        if not style_list:
            raise HTTPException(
                status_code=404,
                detail="No running style data found. Check the netkeiba race ID.",
            )

        entry_repo = EntryRepository(db)
        entries = await entry_repo.get_by_race(race_id)

        updated_count = 0
        for entry in entries:
            # Find matching style info by horse number
            style_info = next(
                (s for s in style_list if s.horse_number == entry.horse_number),
                None
            )
            if style_info and style_info.running_style:
                await entry_repo.update(entry.id, {
                    "running_style": style_info.running_style,
                })
                updated_count += 1

        return FetchResponse(
            success=True,
            message=f"Updated {updated_count} entries with running styles",
            data={
                "updated": updated_count,
                "total_fetched": len(style_list),
                "total_entries": len(entries),
            },
        )


@router.post("/odds/{race_id}", response_model=FetchResponse)
async def fetch_odds(
    race_id: int,
    request: FetchOddsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetch odds and running style from netkeiba result page and update entries."""
    race_repo = RaceRepository(db)
    race = await race_repo.get(race_id)

    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    async with NetkeibaFetcher() as fetcher:
        odds_list = await fetcher.fetch_odds_from_result(request.netkeiba_race_id)

        if not odds_list:
            raise HTTPException(
                status_code=404,
                detail="No odds data found. Make sure the race has finished.",
            )

        entry_repo = EntryRepository(db)
        entries = await entry_repo.get_by_race(race_id)

        updated_count = 0
        for entry in entries:
            # Find matching odds info by horse number
            odds_info = next(
                (o for o in odds_list if o.horse_number == entry.horse_number),
                None
            )
            if odds_info:
                await entry_repo.update(entry.id, {
                    "odds": odds_info.odds,
                    "popularity": odds_info.popularity,
                    "running_style": odds_info.running_style,
                })
                updated_count += 1

        return FetchResponse(
            success=True,
            message=f"Updated {updated_count} entries with odds and running style",
            data={
                "updated": updated_count,
                "total_odds": len(odds_list),
            },
        )
