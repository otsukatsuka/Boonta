"""Data fetch API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/fetch", tags=["fetch"])


class FetchRaceRequest(BaseModel):
    """Request to fetch race data."""

    source_url: str | None = None
    race_id: str | None = None


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
    """Fetch race information from external source."""
    # TODO: Implement netkeiba scraper
    raise HTTPException(
        status_code=501,
        detail="External data fetching not yet implemented",
    )


@router.post("/entries/{race_id}", response_model=FetchResponse)
async def fetch_entries(
    race_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch entry information from external source."""
    # TODO: Implement netkeiba scraper
    raise HTTPException(
        status_code=501,
        detail="External data fetching not yet implemented",
    )


@router.post("/results/{horse_id}", response_model=FetchResponse)
async def fetch_horse_results(
    horse_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch horse results from external source."""
    # TODO: Implement netkeiba scraper
    raise HTTPException(
        status_code=501,
        detail="External data fetching not yet implemented",
    )
