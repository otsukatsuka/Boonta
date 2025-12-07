"""Jockey API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories import JockeyRepository
from app.schemas import (
    JockeyCreate,
    JockeyListResponse,
    JockeyResponse,
    JockeyUpdate,
)

router = APIRouter(prefix="/jockeys", tags=["jockeys"])


@router.get("", response_model=JockeyListResponse)
async def get_jockeys(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get all jockeys with pagination."""
    repo = JockeyRepository(db)
    jockeys = await repo.get_all(skip=skip, limit=limit)
    total = await repo.count()
    return JockeyListResponse(
        items=[JockeyResponse.model_validate(j) for j in jockeys],
        total=total,
    )


@router.get("/search", response_model=list[JockeyResponse])
async def search_jockeys(
    name: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search jockeys by name."""
    repo = JockeyRepository(db)
    jockeys = await repo.search_by_name(name, limit)
    return [JockeyResponse.model_validate(j) for j in jockeys]


@router.get("/{jockey_id}", response_model=JockeyResponse)
async def get_jockey(
    jockey_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a jockey by ID."""
    repo = JockeyRepository(db)
    jockey = await repo.get(jockey_id)
    if not jockey:
        raise HTTPException(status_code=404, detail="Jockey not found")
    return JockeyResponse.model_validate(jockey)


@router.post("", response_model=JockeyResponse, status_code=201)
async def create_jockey(
    data: JockeyCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new jockey."""
    repo = JockeyRepository(db)
    jockey = await repo.create(data.model_dump())
    return JockeyResponse.model_validate(jockey)


@router.put("/{jockey_id}", response_model=JockeyResponse)
async def update_jockey(
    jockey_id: int,
    data: JockeyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a jockey."""
    repo = JockeyRepository(db)
    jockey = await repo.update(jockey_id, data.model_dump(exclude_unset=True))
    if not jockey:
        raise HTTPException(status_code=404, detail="Jockey not found")
    return JockeyResponse.model_validate(jockey)
