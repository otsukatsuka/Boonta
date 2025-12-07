"""Race entry API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories import EntryRepository, RaceRepository
from app.schemas import (
    CommentUpdate,
    EntryCreate,
    EntryListResponse,
    EntryResponse,
    EntryUpdate,
    WorkoutUpdate,
)

router = APIRouter(tags=["entries"])


@router.get("/races/{race_id}/entries", response_model=EntryListResponse)
async def get_race_entries(
    race_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all entries for a race."""
    race_repo = RaceRepository(db)
    race = await race_repo.get(race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    entry_repo = EntryRepository(db)
    entries = await entry_repo.get_by_race(race_id)

    items = []
    for e in entries:
        items.append(EntryResponse(
            id=e.id,
            race_id=e.race_id,
            horse_id=e.horse_id,
            jockey_id=e.jockey_id,
            post_position=e.post_position,
            horse_number=e.horse_number,
            weight=e.weight,
            horse_weight=e.horse_weight,
            horse_weight_diff=e.horse_weight_diff,
            odds=e.odds,
            popularity=e.popularity,
            running_style=e.running_style,
            trainer_comment=e.trainer_comment,
            workout_time=e.workout_time,
            workout_evaluation=e.workout_evaluation,
            workout_course=e.workout_course,
            workout_memo=e.workout_memo,
            created_at=e.created_at,
            updated_at=e.updated_at,
            horse_name=e.horse.name if e.horse else None,
            jockey_name=e.jockey.name if e.jockey else None,
        ))

    return EntryListResponse(items=items, total=len(items))


@router.post("/races/{race_id}/entries", response_model=EntryResponse, status_code=201)
async def add_race_entry(
    race_id: int,
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add an entry to a race."""
    race_repo = RaceRepository(db)
    race = await race_repo.get(race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    if data.race_id != race_id:
        raise HTTPException(status_code=400, detail="race_id in body must match URL")

    entry_repo = EntryRepository(db)

    # Check if entry already exists
    existing = await entry_repo.get_by_race_and_horse(race_id, data.horse_id)
    if existing:
        raise HTTPException(status_code=400, detail="Entry already exists for this horse")

    entry = await entry_repo.create(data.model_dump())
    entry = await entry_repo.get_with_relations(entry.id)

    return EntryResponse(
        id=entry.id,
        race_id=entry.race_id,
        horse_id=entry.horse_id,
        jockey_id=entry.jockey_id,
        post_position=entry.post_position,
        horse_number=entry.horse_number,
        weight=entry.weight,
        horse_weight=entry.horse_weight,
        horse_weight_diff=entry.horse_weight_diff,
        odds=entry.odds,
        popularity=entry.popularity,
        running_style=entry.running_style,
        trainer_comment=entry.trainer_comment,
        workout_time=entry.workout_time,
        workout_evaluation=entry.workout_evaluation,
        workout_course=entry.workout_course,
        workout_memo=entry.workout_memo,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        horse_name=entry.horse.name if entry.horse else None,
        jockey_name=entry.jockey.name if entry.jockey else None,
    )


@router.put("/entries/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: int,
    data: EntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an entry."""
    repo = EntryRepository(db)
    entry = await repo.update(entry_id, data.model_dump(exclude_unset=True))
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry = await repo.get_with_relations(entry_id)

    return EntryResponse(
        id=entry.id,
        race_id=entry.race_id,
        horse_id=entry.horse_id,
        jockey_id=entry.jockey_id,
        post_position=entry.post_position,
        horse_number=entry.horse_number,
        weight=entry.weight,
        horse_weight=entry.horse_weight,
        horse_weight_diff=entry.horse_weight_diff,
        odds=entry.odds,
        popularity=entry.popularity,
        running_style=entry.running_style,
        trainer_comment=entry.trainer_comment,
        workout_time=entry.workout_time,
        workout_evaluation=entry.workout_evaluation,
        workout_course=entry.workout_course,
        workout_memo=entry.workout_memo,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        horse_name=entry.horse.name if entry.horse else None,
        jockey_name=entry.jockey.name if entry.jockey else None,
    )


@router.put("/entries/{entry_id}/workout", response_model=EntryResponse)
async def update_entry_workout(
    entry_id: int,
    data: WorkoutUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update workout information for an entry."""
    repo = EntryRepository(db)
    entry = await repo.update_workout(
        entry_id,
        workout_time=data.workout_time,
        workout_evaluation=data.workout_evaluation.value if data.workout_evaluation else None,
        workout_course=data.workout_course,
        workout_memo=data.workout_memo,
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry = await repo.get_with_relations(entry_id)

    return EntryResponse(
        id=entry.id,
        race_id=entry.race_id,
        horse_id=entry.horse_id,
        jockey_id=entry.jockey_id,
        post_position=entry.post_position,
        horse_number=entry.horse_number,
        weight=entry.weight,
        horse_weight=entry.horse_weight,
        horse_weight_diff=entry.horse_weight_diff,
        odds=entry.odds,
        popularity=entry.popularity,
        running_style=entry.running_style,
        trainer_comment=entry.trainer_comment,
        workout_time=entry.workout_time,
        workout_evaluation=entry.workout_evaluation,
        workout_course=entry.workout_course,
        workout_memo=entry.workout_memo,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        horse_name=entry.horse.name if entry.horse else None,
        jockey_name=entry.jockey.name if entry.jockey else None,
    )


@router.put("/entries/{entry_id}/comment", response_model=EntryResponse)
async def update_entry_comment(
    entry_id: int,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update trainer comment for an entry."""
    repo = EntryRepository(db)
    entry = await repo.update_comment(entry_id, data.trainer_comment)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry = await repo.get_with_relations(entry_id)

    return EntryResponse(
        id=entry.id,
        race_id=entry.race_id,
        horse_id=entry.horse_id,
        jockey_id=entry.jockey_id,
        post_position=entry.post_position,
        horse_number=entry.horse_number,
        weight=entry.weight,
        horse_weight=entry.horse_weight,
        horse_weight_diff=entry.horse_weight_diff,
        odds=entry.odds,
        popularity=entry.popularity,
        running_style=entry.running_style,
        trainer_comment=entry.trainer_comment,
        workout_time=entry.workout_time,
        workout_evaluation=entry.workout_evaluation,
        workout_course=entry.workout_course,
        workout_memo=entry.workout_memo,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        horse_name=entry.horse.name if entry.horse else None,
        jockey_name=entry.jockey.name if entry.jockey else None,
    )
