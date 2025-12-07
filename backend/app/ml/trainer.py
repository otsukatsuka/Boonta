"""Model training with AutoGluon."""

from pathlib import Path
from typing import Any

import pandas as pd

from app.config import get_settings
from app.ml.features import create_derived_features, get_feature_columns, preprocess_features

settings = get_settings()


class ModelTrainer:
    """Trainer for AutoGluon TabularPredictor."""

    def __init__(self, model_path: Path | None = None):
        self.model_path = model_path or settings.model_path / "predictor"
        self.predictor = None

    def train(
        self,
        train_data: pd.DataFrame,
        target: str = "position",
        time_limit: int = 3600,
        presets: str = "best_quality",
    ) -> dict[str, Any]:
        """
        Train the prediction model.

        Args:
            train_data: Training data with features and target
            target: Target column name
            time_limit: Training time limit in seconds
            presets: AutoGluon presets (best_quality, high_quality, medium_quality, optimize_for_deployment)

        Returns:
            Training metrics
        """
        try:
            from autogluon.tabular import TabularPredictor
        except ImportError:
            raise ImportError("AutoGluon is required for training. Install with: pip install autogluon.tabular")

        # Preprocess features
        train_data = preprocess_features(train_data)
        train_data = create_derived_features(train_data)

        # Select feature columns + target
        feature_cols = get_feature_columns()
        available_cols = [c for c in feature_cols if c in train_data.columns]
        available_cols.append(target)

        train_subset = train_data[available_cols].copy()

        # Remove rows with missing target
        train_subset = train_subset.dropna(subset=[target])

        # Train model
        self.predictor = TabularPredictor(
            label=target,
            path=str(self.model_path),
            problem_type="regression",
            eval_metric="mean_absolute_error",
        )

        self.predictor.fit(
            train_data=train_subset,
            time_limit=time_limit,
            presets=presets,
        )

        # Get leaderboard
        leaderboard = self.predictor.leaderboard()

        return {
            "model_path": str(self.model_path),
            "num_training_samples": len(train_subset),
            "feature_count": len(available_cols) - 1,
            "best_model": leaderboard.iloc[0]["model"] if len(leaderboard) > 0 else None,
            "best_score": leaderboard.iloc[0]["score_val"] if len(leaderboard) > 0 else None,
        }

    def train_classification(
        self,
        train_data: pd.DataFrame,
        target: str = "is_place",
        time_limit: int = 3600,
        presets: str = "best_quality",
    ) -> dict[str, Any]:
        """
        Train a binary classification model (place/not place).

        Args:
            train_data: Training data
            target: Target column (is_place: 0 or 1)
            time_limit: Training time limit
            presets: AutoGluon presets

        Returns:
            Training metrics
        """
        try:
            from autogluon.tabular import TabularPredictor
        except ImportError:
            raise ImportError("AutoGluon is required for training")

        # Preprocess
        train_data = preprocess_features(train_data)
        train_data = create_derived_features(train_data)

        feature_cols = get_feature_columns()
        available_cols = [c for c in feature_cols if c in train_data.columns]
        available_cols.append(target)

        train_subset = train_data[available_cols].copy()
        train_subset = train_subset.dropna(subset=[target])

        # Train classification model
        model_path = settings.model_path / "classifier"
        self.predictor = TabularPredictor(
            label=target,
            path=str(model_path),
            problem_type="binary",
            eval_metric="roc_auc",
        )

        self.predictor.fit(
            train_data=train_subset,
            time_limit=time_limit,
            presets=presets,
        )

        leaderboard = self.predictor.leaderboard()

        return {
            "model_path": str(model_path),
            "num_training_samples": len(train_subset),
            "feature_count": len(available_cols) - 1,
            "best_model": leaderboard.iloc[0]["model"] if len(leaderboard) > 0 else None,
            "best_score": leaderboard.iloc[0]["score_val"] if len(leaderboard) > 0 else None,
        }

    def get_feature_importance(self) -> pd.DataFrame | None:
        """Get feature importance from trained model."""
        if self.predictor is None:
            return None

        try:
            return self.predictor.feature_importance()
        except Exception:
            return None
