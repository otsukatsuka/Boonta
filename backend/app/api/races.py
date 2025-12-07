"""Race API routes."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    RaceCreate,
    RaceListResponse,
    RaceResponse,
    RaceUpdate,
)
from app.services import RaceService

router = APIRouter(prefix="/races", tags=["races"])


@router.get("", response_model=RaceListResponse)
async def get_races(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    grade: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all races with pagination."""
    service = RaceService(db)
    races, total = await service.get_races(skip=skip, limit=limit, grade=grade)
    return RaceListResponse(items=races, total=total)


@router.get("/upcoming", response_model=list[RaceResponse])
async def get_upcoming_races(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming races."""
    service = RaceService(db)
    return await service.get_upcoming_races(limit)


@router.get("/search", response_model=list[RaceResponse])
async def search_races(
    name: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search races by name."""
    service = RaceService(db)
    return await service.search_races(name, limit)


@router.get("/by-date", response_model=list[RaceResponse])
async def get_races_by_date_range(
    start_date: date = Query(...),
    end_date: date = Query(...),
    grade: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get races within a date range."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    service = RaceService(db)
    return await service.get_races_by_date_range(start_date, end_date, grade)


@router.get("/{race_id}", response_model=RaceResponse)
async def get_race(
    race_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a race by ID."""
    service = RaceService(db)
    race = await service.get_race(race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    return race


@router.post("", response_model=RaceResponse, status_code=201)
async def create_race(
    data: RaceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new race."""
    service = RaceService(db)
    return await service.create_race(data)


@router.put("/{race_id}", response_model=RaceResponse)
async def update_race(
    race_id: int,
    data: RaceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a race."""
    service = RaceService(db)
    race = await service.update_race(race_id, data)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    return race


@router.delete("/{race_id}", status_code=204)
async def delete_race(
    race_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a race."""
    service = RaceService(db)
    deleted = await service.delete_race(race_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Race not found")
