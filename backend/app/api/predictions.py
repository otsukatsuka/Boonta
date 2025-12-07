"""Prediction API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    PredictionHistoryListResponse,
    PredictionHistoryResponse,
    PredictionResponse,
)
from app.services import PredictionService

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/{race_id}", response_model=PredictionResponse)
async def create_prediction(
    race_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Create a new prediction for a race."""
    service = PredictionService(db)
    prediction = await service.create_prediction(race_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Race not found or no entries")
    return prediction


@router.get("/{race_id}", response_model=PredictionResponse)
async def get_prediction(
    race_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get latest prediction for a race."""
    service = PredictionService(db)
    prediction = await service.get_prediction(race_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return prediction


@router.get("/{race_id}/history", response_model=PredictionHistoryListResponse)
async def get_prediction_history(
    race_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get prediction history for a race."""
    service = PredictionService(db)
    predictions = await service.get_prediction_history(race_id, limit)

    items = [
        PredictionHistoryResponse(
            id=p.id,
            race_id=p.race_id,
            model_version=p.model_version,
            predicted_at=p.predicted_at,
            confidence_score=p.confidence_score,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in predictions
    ]

    return PredictionHistoryListResponse(items=items, total=len(items))
