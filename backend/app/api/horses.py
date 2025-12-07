"""Horse API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories import HorseRepository, ResultRepository
from app.schemas import (
    HorseCreate,
    HorseListResponse,
    HorseResponse,
    HorseUpdate,
    ResultListResponse,
    ResultResponse,
)

router = APIRouter(prefix="/horses", tags=["horses"])


@router.get("", response_model=HorseListResponse)
async def get_horses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get all horses with pagination."""
    repo = HorseRepository(db)
    horses = await repo.get_all(skip=skip, limit=limit)
    total = await repo.count()
    return HorseListResponse(
        items=[HorseResponse.model_validate(h) for h in horses],
        total=total,
    )


@router.get("/search", response_model=list[HorseResponse])
async def search_horses(
    name: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search horses by name."""
    repo = HorseRepository(db)
    horses = await repo.search_by_name(name, limit)
    return [HorseResponse.model_validate(h) for h in horses]


@router.get("/{horse_id}", response_model=HorseResponse)
async def get_horse(
    horse_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a horse by ID."""
    repo = HorseRepository(db)
    horse = await repo.get(horse_id)
    if not horse:
        raise HTTPException(status_code=404, detail="Horse not found")
    return HorseResponse.model_validate(horse)


@router.get("/{horse_id}/results", response_model=ResultListResponse)
async def get_horse_results(
    horse_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get race results for a horse."""
    horse_repo = HorseRepository(db)
    horse = await horse_repo.get(horse_id)
    if not horse:
        raise HTTPException(status_code=404, detail="Horse not found")

    result_repo = ResultRepository(db)
    results = await result_repo.get_by_horse(horse_id, limit)

    items = []
    for r in results:
        items.append(ResultResponse(
            id=r.id,
            race_id=r.race_id,
            horse_id=r.horse_id,
            jockey_id=r.jockey_id,
            position=r.position,
            time=r.time,
            margin=r.margin,
            last_3f=r.last_3f,
            corner_positions=r.corner_positions,
            prize=r.prize,
            created_at=r.created_at,
            updated_at=r.updated_at,
            horse_name=r.horse.name if r.horse else None,
            jockey_name=r.jockey.name if r.jockey else None,
            race_name=r.race.name if r.race else None,
        ))

    return ResultListResponse(items=items, total=len(items))


@router.post("", response_model=HorseResponse, status_code=201)
async def create_horse(
    data: HorseCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new horse."""
    repo = HorseRepository(db)
    horse = await repo.create(data.model_dump())
    return HorseResponse.model_validate(horse)


@router.put("/{horse_id}", response_model=HorseResponse)
async def update_horse(
    horse_id: int,
    data: HorseUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a horse."""
    repo = HorseRepository(db)
    horse = await repo.update(horse_id, data.model_dump(exclude_unset=True))
    if not horse:
        raise HTTPException(status_code=404, detail="Horse not found")
    return HorseResponse.model_validate(horse)
