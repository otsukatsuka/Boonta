"""Modal functions for AutoGluon training and prediction.

IMPORTANT: This module is self-contained. It MUST NOT import from src/.
All preprocessing logic is defined inline to match src/features/ logic.
Keep these in sync when updating features.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from io import StringIO

import modal
import numpy as np
import pandas as pd

# --- Modal App Setup ---
app = modal.App("boonta-ml")

autogluon_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgomp1")
    .pip_install(
        "autogluon.tabular[all]==1.5.1",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
    )
)

model_volume = modal.Volume.from_name("boonta-models", create_if_missing=True)
VOLUME_PATH = "/models"

# --- Inline Preprocessing (mirrors src/features/) ---

CATEGORICAL_COLS = [
    "pace_forecast", "tenkai_symbol", "running_style",
    "distance_aptitude", "heavy_track_code",
]

NUMERICAL_DEFAULTS = {
    "idm": 50.0,
    "jockey_index": 50.0,
    "info_index": 50.0,
    "overall_index": 50.0,
    "training_index": 50.0,
    "stable_index": 50.0,
    "ten_index": 50.0,
    "pace_index": 50.0,
    "agari_index": 50.0,
    "position_index": 50.0,
    "odds": 10.0,
    "popularity": 8,
    "horse_number": 5,
    "waku": 4,
    "weight_carried": 55.0,
    "mid_position": 8,
    "mid_gap": 5,
    "mid_position_io": 3,
    "late3f_position": 8,
    "late3f_gap": 5,
    "late3f_io": 3,
    "goal_position": 8,
    "goal_gap": 5,
    "goal_io": 3,
    "start_index": 50.0,
    "gate_miss_rate": 5.0,
    "upset_index": 50,
    "speed_balance": 0.0,
    "position_delta": 0.0,
    "io_shift": 0.0,
    "log_odds": 2.3,
    "risk_score": 0.5,
    "race_head_count": 16,
}


def preprocess_features(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing values and cast types. Mirrors src/features/engineering.preprocess()."""
    df = df.copy()
    for col in CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)
    for col, default in NUMERICAL_DEFAULTS.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)
    return df


def create_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features. Mirrors src/features/derived.add_derived_features()."""
    df = df.copy()
    if "ten_index" in df.columns and "agari_index" in df.columns:
        df["speed_balance"] = df["ten_index"] - df["agari_index"]
    if "goal_position" in df.columns and "mid_position" in df.columns:
        df["position_delta"] = df["goal_position"] - df["mid_position"]
    if "goal_io" in df.columns and "mid_position_io" in df.columns:
        df["io_shift"] = df["goal_io"] - df["mid_position_io"]
    if "odds" in df.columns:
        df["log_odds"] = np.log(df["odds"].clip(lower=1.0))
    if "gate_miss_rate" in df.columns and "start_index" in df.columns:
        df["risk_score"] = df["gate_miss_rate"] * (1 - df["start_index"] / 10)
    return df


# --- Modal Functions ---

@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=7200,
    memory=8192,
    cpu=4.0,
)
def train_model(
    training_data_csv: str,
    model_name: str = "jrdb_predictor",
    time_limit: int = 1800,
    presets: str = "best_quality",
    excluded_model_types: list[str] | None = None,
) -> dict:
    """Train an AutoGluon model on JRDB feature data."""
    from autogluon.tabular import TabularPredictor

    df = pd.read_csv(StringIO(training_data_csv))
    df = preprocess_features(df)
    df = create_derived_features(df)

    label = "is_place"
    if label not in df.columns:
        return {"success": False, "error": f"Label column '{label}' not found"}

    df = df.dropna(subset=[label])
    print(f"Training with {len(df)} samples, {len(df.columns)} columns")

    model_path = os.path.join(VOLUME_PATH, model_name)
    predictor = TabularPredictor(
        label=label,
        path=model_path,
        problem_type="binary",
        eval_metric="roc_auc",
    )

    fit_kwargs = {
        "train_data": df,
        "time_limit": time_limit,
        "presets": presets,
    }
    if excluded_model_types:
        fit_kwargs["excluded_model_types"] = excluded_model_types

    predictor.fit(**fit_kwargs)

    leaderboard = predictor.leaderboard(silent=True)
    best_score = float(leaderboard["score_val"].max()) if len(leaderboard) > 0 else None
    best_model = leaderboard.iloc[0]["model"] if len(leaderboard) > 0 else "unknown"

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "num_samples": len(df),
        "presets": presets,
        "best_model": str(best_model),
        "best_score": best_score,
    }
    metadata_path = os.path.join(VOLUME_PATH, model_name, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)

    model_volume.commit()

    return {
        "success": True,
        "model_path": model_path,
        "num_samples": len(df),
        "presets_used": presets,
        "best_model": str(best_model),
        "best_score": best_score,
        "trained_at": metadata["trained_at"],
    }


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=60,
    memory=4096,
)
def predict(
    features_json: str,
    model_name: str = "jrdb_predictor",
) -> dict:
    """Predict is_place probabilities for given features."""
    from autogluon.tabular import TabularPredictor

    try:
        model_path = os.path.join(VOLUME_PATH, model_name)
        predictor = TabularPredictor.load(model_path)

        features = json.loads(features_json)
        df = pd.DataFrame(features)
        df = preprocess_features(df)
        df = create_derived_features(df)

        proba = predictor.predict_proba(df)
        if isinstance(proba, pd.DataFrame) and 1 in proba.columns:
            predictions = proba[1].tolist()
        else:
            predictions = proba.iloc[:, -1].tolist()

        return {"success": True, "predictions": predictions}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=30,
)
def get_model_status(model_name: str = "jrdb_predictor") -> dict:
    """Check if a trained model exists on the volume."""
    model_path = os.path.join(VOLUME_PATH, model_name)

    if not os.path.exists(model_path):
        return {"exists": False, "model_name": model_name}

    files = os.listdir(model_path)
    predictor_exists = "predictor.pkl" in files

    metadata = None
    metadata_path = os.path.join(model_path, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)

    return {
        "exists": True,
        "model_name": model_name,
        "files": files,
        "predictor_exists": predictor_exists,
        "trained_at": metadata.get("trained_at") if metadata else None,
        "best_score": metadata.get("best_score") if metadata else None,
        "num_samples": metadata.get("num_samples") if metadata else None,
    }


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=60,
    memory=4096,
)
def get_feature_importance(model_name: str = "jrdb_predictor") -> dict:
    """Get feature importance from a trained model."""
    from autogluon.tabular import TabularPredictor

    try:
        model_path = os.path.join(VOLUME_PATH, model_name)
        predictor = TabularPredictor.load(model_path)
        importance_df = predictor.feature_importance()

        features = []
        for name, row in importance_df.iterrows():
            imp = row["importance"] if "importance" in row.index else row.iloc[0]
            features.append({"name": str(name), "importance": float(imp)})

        features.sort(key=lambda x: x["importance"], reverse=True)
        return {"success": True, "features": features}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Local Entrypoints ---

@app.local_entrypoint()
def test_status():
    """Check model status."""
    result = get_model_status.remote()
    print(f"Model status: {result}")


@app.local_entrypoint()
def test_train():
    """Run a quick test training."""
    import pathlib
    csv_path = pathlib.Path("data/processed/training.csv")
    if not csv_path.exists():
        print(f"Training data not found at {csv_path}")
        return
    csv_data = csv_path.read_text()
    result = train_model.remote(
        training_data_csv=csv_data,
        time_limit=300,
        presets="medium_quality",
    )
    print(f"Training result: {result}")
