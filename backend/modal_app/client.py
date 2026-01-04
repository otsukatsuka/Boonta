"""Client for calling Modal functions from FastAPI."""

import json
from typing import Any

import modal


class ModalClient:
    """Wrapper for Modal function calls."""

    def __init__(self, app_name: str = "boonta-ml"):
        self.app_name = app_name
        self._predict_fn = None
        self._train_fn = None
        self._status_fn = None
        self._importance_fn = None

    def _get_function(self, name: str) -> modal.Function:
        """Get a Modal function by name."""
        return modal.Function.from_name(self.app_name, name)

    async def predict(
        self,
        features: list[dict[str, Any]],
        model_name: str = "place_predictor",
    ) -> dict:
        """Call Modal predict function.

        Args:
            features: List of feature dictionaries
            model_name: Name of the model to use

        Returns:
            dict with predictions or error
        """
        try:
            predict_fn = self._get_function("predict")
            result = predict_fn.remote(
                features_json=json.dumps(features),
                model_name=model_name,
            )
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def train(
        self,
        training_data_csv: str,
        model_name: str = "place_predictor",
        time_limit: int = 1800,
        presets: str = "best_quality",
    ) -> dict:
        """Call Modal train function (async spawn).

        Args:
            training_data_csv: CSV content as string
            model_name: Name for the model
            time_limit: Training time limit in seconds
            presets: AutoGluon presets

        Returns:
            dict with call_id for status tracking
        """
        try:
            train_fn = self._get_function("train_model")

            # Spawn for long-running task
            call = train_fn.spawn(
                training_data_csv=training_data_csv,
                model_name=model_name,
                time_limit=time_limit,
                presets=presets,
            )

            return {"success": True, "call_id": call.object_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def train_sync(
        self,
        training_data_csv: str,
        model_name: str = "place_predictor",
        time_limit: int = 1800,
        presets: str = "best_quality",
    ) -> dict:
        """Call Modal train function synchronously (waits for completion).

        Args:
            training_data_csv: CSV content as string
            model_name: Name for the model
            time_limit: Training time limit in seconds
            presets: AutoGluon presets

        Returns:
            dict with training results
        """
        try:
            train_fn = self._get_function("train_model")
            result = train_fn.remote(
                training_data_csv=training_data_csv,
                model_name=model_name,
                time_limit=time_limit,
                presets=presets,
            )
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_training_status(self, call_id: str) -> dict:
        """Check training job status.

        Args:
            call_id: The call ID from train()

        Returns:
            dict with status and result (if completed)
        """
        try:
            call = modal.FunctionCall.from_id(call_id)

            try:
                result = call.get(timeout=0)  # Non-blocking
                return {"status": "completed", "result": result}
            except TimeoutError:
                return {"status": "running"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_model_status(self, model_name: str = "place_predictor") -> dict:
        """Check model status on Modal Volume.

        Args:
            model_name: Name of the model

        Returns:
            dict with model status
        """
        try:
            status_fn = self._get_function("get_model_status")
            return status_fn.remote(model_name=model_name)
        except Exception as e:
            return {"exists": False, "error": str(e)}

    async def get_feature_importance(
        self, model_name: str = "place_predictor"
    ) -> dict:
        """Get feature importance from Modal.

        Args:
            model_name: Name of the model

        Returns:
            dict with feature importance
        """
        try:
            importance_fn = self._get_function("get_feature_importance")
            return importance_fn.remote(model_name=model_name)
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
_modal_client: ModalClient | None = None


def get_modal_client() -> ModalClient:
    """Get Modal client singleton."""
    global _modal_client
    if _modal_client is None:
        _modal_client = ModalClient()
    return _modal_client
