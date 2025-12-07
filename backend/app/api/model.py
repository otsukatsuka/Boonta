"""Model API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas import FeatureImportanceResponse, ModelStatusResponse

router = APIRouter(prefix="/model", tags=["model"])

settings = get_settings()


@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status(
    db: AsyncSession = Depends(get_db),
):
    """Get current model status."""
    # Check if model exists
    model_path = settings.model_path / "predictor"
    is_trained = model_path.exists()

    return ModelStatusResponse(
        model_version=settings.model_version,
        is_trained=is_trained,
        last_trained_at=None,  # TODO: Read from model metadata
        training_data_count=0,  # TODO: Count from DB
        metrics=None,
    )


@router.post("/train")
async def train_model(
    db: AsyncSession = Depends(get_db),
):
    """Train the prediction model."""
    # TODO: Implement actual training
    raise HTTPException(
        status_code=501,
        detail="Model training not yet implemented. Use AutoGluon training script.",
    )


@router.get("/feature-importance", response_model=FeatureImportanceResponse)
async def get_feature_importance(
    db: AsyncSession = Depends(get_db),
):
    """Get feature importance from the trained model."""
    model_path = settings.model_path / "predictor"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model not trained yet")

    # TODO: Load actual feature importance from AutoGluon model
    return FeatureImportanceResponse(
        features=[
            {"name": "odds", "importance": 0.25},
            {"name": "jockey_win_rate", "importance": 0.15},
            {"name": "avg_position_last5", "importance": 0.12},
            {"name": "running_style", "importance": 0.10},
            {"name": "workout_evaluation", "importance": 0.08},
        ]
    )
