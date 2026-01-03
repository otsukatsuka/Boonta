"""
Train ML model for horse racing prediction using AutoGluon.

This script trains a model to predict whether a horse will place (finish in top 3).

Usage:
    python scripts/train_model.py                         # G1 + G3 (default)
    python scripts/train_model.py --grade G3              # G3 only
    python scripts/train_model.py --grade all             # G1 + G3 combined
    python scripts/train_model.py --with-history          # With horse history features
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
from autogluon.tabular import TabularPredictor

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_and_preprocess_data(csv_path: str) -> pd.DataFrame:
    """Load and preprocess training data from CSV file."""
    print(f"Loading data from {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} records")
    return load_and_preprocess_data_from_df(df)


def load_and_preprocess_data_from_df(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess training data from DataFrame."""
    print(f"Preprocessing {len(df)} records")

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

    # Add horse history features if available (from --with-history collection)
    history_features = [
        "total_races",
        "total_wins",
        "total_places",
        "grade_wins",
        "win_rate",
        "place_rate",
        "avg_position_last5",
        "days_since_last_race",
    ]
    for feat in history_features:
        if feat in df.columns and df[feat].notna().any():
            df[feat] = df[feat].fillna(df[feat].median() if df[feat].dtype in ['float64', 'int64'] else 0)
            features.append(feat)

    # Add history last_3f features
    if "best_last_3f" in df.columns and df["best_last_3f"].notna().any():
        df["best_last_3f"] = df["best_last_3f"].fillna(df["best_last_3f"].median())
        features.append("best_last_3f")

    if "avg_last_3f_hist" in df.columns and df["avg_last_3f_hist"].notna().any():
        df["avg_last_3f_hist"] = df["avg_last_3f_hist"].fillna(df["avg_last_3f_hist"].median())
        features.append("avg_last_3f_hist")

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


def load_combined_data(data_dir: str, grades: list[str], with_history: bool = False) -> pd.DataFrame:
    """Load and combine data from multiple grade CSV files."""
    dfs = []
    suffix = "_hist" if with_history else ""

    for grade in grades:
        csv_path = os.path.join(data_dir, f"{grade.lower()}_races{suffix}.csv")
        # Fallback to non-history file if history file doesn't exist
        if not os.path.exists(csv_path) and with_history:
            csv_path = os.path.join(data_dir, f"{grade.lower()}_races.csv")
            print(f"Warning: History file not found, using {csv_path}")

        if os.path.exists(csv_path):
            print(f"Loading {grade} data from {csv_path}")
            df = pd.read_csv(csv_path)
            print(f"  Loaded {len(df)} records")
            dfs.append(df)
        else:
            print(f"Warning: {csv_path} not found, skipping...")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal combined records: {len(combined)}")
    return combined


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Train ML model for horse racing prediction")
    parser.add_argument(
        "--grade",
        choices=["G1", "G3", "all"],
        default="all",
        help="Grade to train on (default: all = G1 + G3 combined)",
    )
    parser.add_argument(
        "--with-history",
        action="store_true",
        help="Use data with horse history features (requires _hist.csv files)",
    )
    args = parser.parse_args()

    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data", "training")
    model_dir = os.path.join(script_dir, "..", "models", "place_predictor")

    # Determine which grades to load
    if args.grade == "all":
        grades = ["G1", "G3"]
    else:
        grades = [args.grade]

    # Load data
    df = load_combined_data(data_dir, grades, with_history=args.with_history)
    if df.empty:
        print("Error: No training data found.")
        print("Please run collect_training_data.py first.")
        sys.exit(1)

    # Preprocess
    df = load_and_preprocess_data_from_df(df)

    if len(df) < 100:
        print("Warning: Less than 100 training samples. Model may not be reliable.")

    # Create model directory
    os.makedirs(os.path.dirname(model_dir), exist_ok=True)

    # Train model
    grade_str = "+".join(grades)
    hist_str = " (with horse history)" if args.with_history else ""
    print("\n" + "=" * 50)
    print(f"Training model for place prediction (top 3) using {grade_str} data{hist_str}")
    print("=" * 50)

    predictor = train_model(df, model_dir, target="is_place")

    print(f"\nModel saved to: {model_dir}")
    print("\nYou can now use this model in the prediction service!")


if __name__ == "__main__":
    main()
