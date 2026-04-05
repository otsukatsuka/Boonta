"""Synchronous Modal client for CLI usage."""
from __future__ import annotations

import json

import modal


class ModalClient:
    """Synchronous wrapper for calling Modal functions from CLI."""

    def __init__(self, app_name: str = "boonta-ml"):
        self.app_name = app_name

    def _get_function(self, name: str) -> modal.Function:
        return modal.Function.from_name(self.app_name, name)

    def train(
        self,
        csv_data: str,
        model_name: str = "jrdb_predictor",
        time_limit: int = 1800,
        presets: str = "best_quality",
    ) -> dict:
        """Start training and wait for completion."""
        train_fn = self._get_function("train_model")
        return train_fn.remote(
            training_data_csv=csv_data,
            model_name=model_name,
            time_limit=time_limit,
            presets=presets,
        )

    def train_async(
        self,
        csv_data: str,
        model_name: str = "jrdb_predictor",
        time_limit: int = 1800,
        presets: str = "best_quality",
    ) -> str:
        """Start training asynchronously, return call_id for status polling."""
        train_fn = self._get_function("train_model")
        call = train_fn.spawn(
            training_data_csv=csv_data,
            model_name=model_name,
            time_limit=time_limit,
            presets=presets,
        )
        return call.object_id

    def get_training_status(self, call_id: str) -> dict:
        """Check status of an async training job."""
        call = modal.FunctionCall.from_id(call_id)
        try:
            result = call.get(timeout=0)
            return {"status": "completed", "result": result}
        except TimeoutError:
            return {"status": "running"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def predict(
        self,
        features: list[dict],
        model_name: str = "jrdb_predictor",
    ) -> dict:
        """Get is_place probability predictions."""
        predict_fn = self._get_function("predict")
        return predict_fn.remote(
            features_json=json.dumps(features),
            model_name=model_name,
        )

    def get_model_status(self, model_name: str = "jrdb_predictor") -> dict:
        """Check if model exists and get metadata."""
        status_fn = self._get_function("get_model_status")
        return status_fn.remote(model_name=model_name)

    def get_feature_importance(self, model_name: str = "jrdb_predictor") -> dict:
        """Get feature importance from trained model."""
        importance_fn = self._get_function("get_feature_importance")
        return importance_fn.remote(model_name=model_name)
