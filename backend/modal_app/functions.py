"""Modal functions for Boonta ML training and prediction.

Usage:
    # Local test (without deploying)
    modal run modal_app/functions.py::test_status

    # Deploy to Modal
    modal deploy modal_app/functions.py

    # Run training locally (for testing)
    modal run modal_app/functions.py::train_model --training-data-csv "$(cat data/training/g1_races.csv)"
"""

import json
import os
from io import StringIO

import modal

# ============================================================
# Modal Configuration (self-contained, no external imports)
# ============================================================

app = modal.App("boonta-ml")

# Modal Image with Python 3.12 and AutoGluon 1.5.0 (full dependencies)
autogluon_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgomp1")
    .pip_install(
        "autogluon.tabular[all]==1.5.0",  # Full install with all model types
        "pandas>=2.0.0",
        "numpy>=1.24.0",
    )
)

# Modal Volume for persistent model storage
model_volume = modal.Volume.from_name("boonta-models", create_if_missing=True)
VOLUME_PATH = "/models"


# ============================================================
# Feature Engineering (inline copy from app/ml/features.py)
# ============================================================

def preprocess_features(df):
    """Preprocess features for model training/prediction."""
    import numpy as np
    import pandas as pd

    df = df.copy()

    categorical_cols = [
        "horse_sex", "course_type", "venue", "track_condition",
        "weather", "running_style", "workout_evaluation",
    ]
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    numerical_defaults = {
        "horse_age": 4, "horse_weight": 480, "horse_weight_diff": 0,
        "distance": 2000, "post_position": 5, "horse_number": 5,
        "weight": 55, "odds": 10.0, "popularity": 8,
        "avg_position_last5": 5.0, "win_rate": 0.1, "place_rate": 0.3,
        "avg_last_3f": 35.0, "best_last_3f": 34.0, "days_since_last_race": 30,
        "jockey_win_rate": 0.1, "jockey_venue_win_rate": 0.1,
        "escape_horse_count": 1, "front_horse_count": 4,
        "is_inner_post": 0, "is_outer_post": 0,
        "rest_flag": 0, "short_rotation_flag": 0,
        "same_distance_win_rate": 0.1, "same_distance_place_rate": 0.3,
        "same_venue_win_rate": 0.1, "same_venue_place_rate": 0.3,
        "same_track_condition_place_rate": 0.3,
    }
    for col, default in numerical_defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)

    return df


def create_derived_features(df):
    """Create derived features from base features."""
    import numpy as np

    df = df.copy()

    if "post_position" in df.columns:
        df["is_inner_post"] = (df["post_position"] <= 3).astype(int)
        df["is_outer_post"] = (df["post_position"] >= 6).astype(int)

    if "days_since_last_race" in df.columns:
        df["rest_flag"] = (df["days_since_last_race"] >= 70).astype(int)
        df["short_rotation_flag"] = (df["days_since_last_race"] <= 14).astype(int)

    if "odds" in df.columns:
        df["log_odds"] = df["odds"].apply(lambda x: np.log(x) if x > 0 else 0)

    if "weight" in df.columns and "horse_weight" in df.columns:
        df["weight_ratio"] = df["weight"] / df["horse_weight"]

    if "avg_position_last5" in df.columns and "win_rate" in df.columns:
        df["form_score"] = (1 / df["avg_position_last5"]) * df["win_rate"]

    return df


# ============================================================
# Modal Functions
# ============================================================

@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=3600,
    memory=8192,
    cpu=4.0,
)
def train_model(
    training_data_csv: str,
    model_name: str = "place_predictor",
    time_limit: int = 1800,
    presets: str = "best_quality",
) -> dict:
    """Train AutoGluon model on Modal."""
    import pandas as pd
    from autogluon.tabular import TabularPredictor

    # Parse training data
    df = pd.read_csv(StringIO(training_data_csv))
    print(f"Loaded {len(df)} training samples")

    # Preprocess features
    df = preprocess_features(df)
    df = create_derived_features(df)

    # Check for target column
    if "is_place" not in df.columns:
        return {"success": False, "error": "Target column 'is_place' not found"}

    df = df.dropna(subset=["is_place"])
    print(f"After dropping NaN targets: {len(df)} samples")

    model_path = f"{VOLUME_PATH}/{model_name}"

    # Use "extreme" preset for small datasets (new in AutoGluon 1.5.0)
    if len(df) < 30000 and presets == "best_quality":
        presets = "extreme"
        print("Using 'extreme' preset for small dataset (<30k samples)")

    predictor = TabularPredictor(
        label="is_place",
        path=model_path,
        problem_type="binary",
        eval_metric="roc_auc",
    )

    predictor.fit(
        train_data=df,
        time_limit=time_limit,
        presets=presets,
    )

    leaderboard = predictor.leaderboard()

    # Commit volume to persist model
    model_volume.commit()

    return {
        "success": True,
        "model_path": model_path,
        "num_samples": len(df),
        "presets_used": presets,
        "best_model": str(leaderboard.iloc[0]["model"]) if len(leaderboard) > 0 else None,
        "best_score": float(leaderboard.iloc[0]["score_val"]) if len(leaderboard) > 0 else None,
    }


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=60,
    memory=4096,
)
def predict(
    features_json: str,
    model_name: str = "place_predictor",
) -> dict:
    """Make predictions using trained model on Modal."""
    import pandas as pd
    from autogluon.tabular import TabularPredictor

    model_path = f"{VOLUME_PATH}/{model_name}"

    if not os.path.exists(model_path):
        return {"success": False, "error": f"Model not found at {model_path}"}

    try:
        predictor = TabularPredictor.load(model_path)
    except Exception as e:
        return {"success": False, "error": f"Failed to load model: {e}"}

    features = json.loads(features_json)
    df = pd.DataFrame(features)

    df = preprocess_features(df)
    df = create_derived_features(df)

    try:
        proba = predictor.predict_proba(df)

        if 1 in proba.columns:
            place_proba = proba[1].tolist()
        else:
            place_proba = proba.iloc[:, 1].tolist()

        return {"success": True, "predictions": place_proba}
    except Exception as e:
        return {"success": False, "error": f"Prediction failed: {e}"}


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=30,
)
def get_model_status(model_name: str = "place_predictor") -> dict:
    """Check model status on Modal Volume."""
    from pathlib import Path

    model_path = Path(f"{VOLUME_PATH}/{model_name}")

    if not model_path.exists():
        return {"exists": False, "model_name": model_name}

    predictor_file = model_path / "predictor.pkl"

    return {
        "exists": True,
        "model_name": model_name,
        "files": os.listdir(model_path),
        "predictor_exists": predictor_file.exists(),
    }


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=60,
    memory=4096,
)
def get_feature_importance(model_name: str = "place_predictor") -> dict:
    """Get feature importance from trained model."""
    from autogluon.tabular import TabularPredictor

    model_path = f"{VOLUME_PATH}/{model_name}"

    if not os.path.exists(model_path):
        return {"success": False, "error": f"Model not found at {model_path}"}

    try:
        predictor = TabularPredictor.load(model_path)
        importance = predictor.feature_importance()

        features = []
        for name, row in importance.iterrows():
            importance_value = (
                float(row["importance"]) if "importance" in row else float(row.iloc[0])
            )
            features.append({"name": str(name), "importance": importance_value})

        features.sort(key=lambda x: x["importance"], reverse=True)

        return {"success": True, "features": features}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Local Test Functions
# ============================================================

@app.local_entrypoint()
def test_status():
    """Test: Check model status on Modal."""
    print("Checking model status...")
    result = get_model_status.remote()
    print(f"Result: {result}")
    return result


@app.local_entrypoint()
def test_train():
    """Test: Train with sample data."""
    from pathlib import Path

    csv_path = Path(__file__).parent.parent / "data" / "training" / "g1_races.csv"
    if not csv_path.exists():
        print(f"Training data not found: {csv_path}")
        return

    print(f"Loading training data from {csv_path}...")
    training_data = csv_path.read_text()

    print("Starting training on Modal...")
    result = train_model.remote(
        training_data_csv=training_data,
        time_limit=300,  # 5 minutes for testing
        presets="medium_quality",  # Faster for testing
    )
    print(f"Result: {result}")
    return result
