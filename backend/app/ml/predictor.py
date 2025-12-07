"""Model prediction with AutoGluon."""

from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.ml.features import create_derived_features, get_feature_columns, preprocess_features

settings = get_settings()


class ModelPredictor:
    """Predictor using trained AutoGluon model."""

    def __init__(self, model_path: Path | None = None):
        self.model_path = model_path or settings.model_path / "predictor"
        self.predictor = None
        self._load_model()

    def _load_model(self):
        """Load the trained model."""
        if not self.model_path.exists():
            self.predictor = None
            return

        try:
            from autogluon.tabular import TabularPredictor

            self.predictor = TabularPredictor.load(str(self.model_path))
        except ImportError:
            self.predictor = None
        except Exception:
            self.predictor = None

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.predictor is not None

    def predict(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Predict positions for race entries.

        Args:
            data: DataFrame with features for each entry

        Returns:
            DataFrame with predictions added
        """
        if not self.is_loaded:
            # Return simple odds-based prediction if model not loaded
            return self._fallback_predict(data)

        # Preprocess
        data = preprocess_features(data)
        data = create_derived_features(data)

        # Get feature columns that exist
        feature_cols = get_feature_columns()
        available_cols = [c for c in feature_cols if c in data.columns]

        # Predict
        predictions = self.predictor.predict(data[available_cols])
        data["predicted_position"] = predictions

        return data

    def predict_proba(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Predict probabilities for place (top 3).

        Args:
            data: DataFrame with features

        Returns:
            DataFrame with probability predictions
        """
        classifier_path = settings.model_path / "classifier"

        if not classifier_path.exists():
            return self._fallback_predict_proba(data)

        try:
            from autogluon.tabular import TabularPredictor

            classifier = TabularPredictor.load(str(classifier_path))

            # Preprocess
            data = preprocess_features(data)
            data = create_derived_features(data)

            feature_cols = get_feature_columns()
            available_cols = [c for c in feature_cols if c in data.columns]

            # Predict probabilities
            proba = classifier.predict_proba(data[available_cols])
            data["place_probability"] = proba[1] if 1 in proba.columns else proba.iloc[:, 1]

            return data

        except Exception:
            return self._fallback_predict_proba(data)

    def _fallback_predict(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fallback prediction using odds."""
        data = data.copy()

        if "odds" in data.columns:
            # Lower odds = better predicted position
            data["predicted_position"] = data["odds"].rank()
        else:
            data["predicted_position"] = range(1, len(data) + 1)

        return data

    def _fallback_predict_proba(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fallback probability using odds."""
        data = data.copy()

        if "odds" in data.columns:
            # Convert odds to probability
            total_implied_prob = (1 / data["odds"]).sum()
            data["place_probability"] = (1 / data["odds"]) / total_implied_prob * 3
            data["place_probability"] = data["place_probability"].clip(0, 1)
        else:
            data["place_probability"] = 0.3

        return data

    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        if not self.is_loaded:
            return {
                "loaded": False,
                "path": str(self.model_path),
            }

        return {
            "loaded": True,
            "path": str(self.model_path),
            "model_names": self.predictor.get_model_names() if self.predictor else [],
        }
