"""
Train ML model for horse racing prediction using AutoGluon.

This script trains a model to predict whether a horse will place (finish in top 3).
"""

import os
import sys

import numpy as np
import pandas as pd
from autogluon.tabular import TabularPredictor

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_and_preprocess_data(csv_path: str) -> pd.DataFrame:
    """Load and preprocess training data."""
    print(f"Loading data from {csv_path}")
    df = pd.read_csv(csv_path)

    print(f"Loaded {len(df)} records")

    # Drop rows with missing critical values
    df = df.dropna(subset=["position", "odds", "running_style"])

    # Filter out invalid positions (non-finished horses)
    df = df[df["position"] > 0]

    print(f"After filtering: {len(df)} records")

    # Feature engineering
    # 1. Normalize odds (log transform to reduce skewness)
    df["log_odds"] = df["odds"].apply(lambda x: np.log(x + 1) if x > 0 else 0)

    # 2. Create running style encoding
    style_map = {
        "ESCAPE": 1,
        "FRONT": 2,
        "STALKER": 3,
        "CLOSER": 4,
        "VERSATILE": 2.5,
    }
    df["running_style_code"] = df["running_style"].map(style_map).fillna(2.5)

    # 3. Course type encoding
    df["is_turf"] = (df["course_type"] == "芝").astype(int)

    # 4. Venue encoding
    venues = df["venue"].unique()
    venue_map = {v: i for i, v in enumerate(venues)}
    df["venue_code"] = df["venue"].map(venue_map)

    # 5. Grade encoding
    grade_map = {"G1": 1, "G2": 2, "G3": 3, "OP": 4}
    df["grade_code"] = df["grade"].map(grade_map).fillna(4)

    print("\nData summary:")
    print(f"  Total records: {len(df)}")
    print(f"  Win rate: {df['is_win'].mean():.3f}")
    print(f"  Place rate: {df['is_place'].mean():.3f}")
    print(f"  Running styles: {df['running_style'].value_counts().to_dict()}")

    return df


def train_model(df: pd.DataFrame, model_dir: str, target: str = "is_place"):
    """Train AutoGluon model."""
    # Select features for training
    features = [
        "horse_number",
        "odds",
        "popularity",
        "running_style_code",
        "distance",
        "is_turf",
        "grade_code",
        "weight",
        "log_odds",
    ]

    # Add optional features if available
    if "horse_weight" in df.columns and df["horse_weight"].notna().any():
        df["horse_weight"] = df["horse_weight"].fillna(df["horse_weight"].median())
        features.append("horse_weight")

    if "last_3f" in df.columns and df["last_3f"].notna().any():
        df["last_3f"] = df["last_3f"].fillna(df["last_3f"].median())
        features.append("last_3f")

    # Prepare training data
    train_data = df[features + [target]].copy()

    print(f"\nTraining features: {features}")
    print(f"Target: {target}")
    print(f"Training samples: {len(train_data)}")

    # Initialize and train predictor
    predictor = TabularPredictor(
        label=target,
        path=model_dir,
        problem_type="binary",
        eval_metric="roc_auc",
    )

    # Train with various models
    predictor.fit(
        train_data,
        time_limit=300,  # 5 minutes max
        presets="medium_quality",  # Balance quality and speed
        verbosity=2,
    )

    # Show results
    print("\n" + "=" * 50)
    print("Training complete!")
    print("=" * 50)

    # Leaderboard
    print("\nModel Leaderboard:")
    print(predictor.leaderboard(silent=True))

    # Feature importance
    print("\nFeature Importance:")
    importance = predictor.feature_importance(train_data)
    print(importance)

    return predictor


def main():
    """Main entry point."""
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data", "training")
    model_dir = os.path.join(script_dir, "..", "models", "place_predictor")

    csv_path = os.path.join(data_dir, "g1_races.csv")

    # Check if data exists
    if not os.path.exists(csv_path):
        print(f"Error: Training data not found at {csv_path}")
        print("Please run collect_training_data.py first.")
        sys.exit(1)

    # Load and preprocess
    df = load_and_preprocess_data(csv_path)

    if len(df) < 100:
        print("Warning: Less than 100 training samples. Model may not be reliable.")

    # Create model directory
    os.makedirs(os.path.dirname(model_dir), exist_ok=True)

    # Train model
    print("\n" + "=" * 50)
    print("Training model for place prediction (top 3)")
    print("=" * 50)

    predictor = train_model(df, model_dir, target="is_place")

    print(f"\nModel saved to: {model_dir}")
    print("\nYou can now use this model in the prediction service!")


if __name__ == "__main__":
    main()
