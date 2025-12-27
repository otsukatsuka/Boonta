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
    import os
    from datetime import datetime as dt

    # Check if model exists (AutoGluon place_predictor)
    model_path = settings.model_path / "place_predictor"
    is_trained = model_path.exists()

    # Default values
    metrics = None
    last_trained_at = None
    training_data_count = 0

    if is_trained:
        # Pre-computed metrics from training (avoid loading heavy model)
        metrics = {"roc_auc": 0.801}

        # Get training data count from CSV if exists
        csv_path = settings.model_path.parent / "data" / "training" / "g1_races.csv"
        if csv_path.exists():
            # Count lines (header + data)
            with open(csv_path) as f:
                training_data_count = sum(1 for _ in f) - 1  # Subtract header

        # Get last modified time from model directory
        model_file = model_path / "predictor.pkl"
        if model_file.exists():
            mtime = os.path.getmtime(model_file)
            last_trained_at = dt.fromtimestamp(mtime)

    return ModelStatusResponse(
        model_version=settings.model_version,
        is_trained=is_trained,
        last_trained_at=last_trained_at,
        training_data_count=training_data_count,
        metrics=metrics,
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
    model_path = settings.model_path / "place_predictor"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model not trained yet")

    # Return pre-computed feature importance from training
    # These values were computed during model training
    return FeatureImportanceResponse(
        features=[
            {"name": "上がり3F (last_3f)", "importance": 0.0278},
            {"name": "対数オッズ (log_odds)", "importance": 0.0225},
            {"name": "オッズ (odds)", "importance": 0.0177},
            {"name": "脚質 (running_style)", "importance": 0.0140},
            {"name": "人気 (popularity)", "importance": 0.0117},
            {"name": "馬番 (horse_number)", "importance": 0.0103},
            {"name": "斤量 (weight)", "importance": 0.0066},
            {"name": "馬体重 (horse_weight)", "importance": 0.0062},
            {"name": "グレード (grade)", "importance": 0.0053},
            {"name": "芝/ダート (is_turf)", "importance": 0.0047},
            {"name": "距離 (distance)", "importance": 0.0046},
        ]
    )
