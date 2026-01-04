"""Feature engineering for ML model (Modal version).

This is a copy of app/ml/features.py for use in Modal functions.
Keep this in sync with the original file.
"""

import numpy as np
import pandas as pd


def preprocess_features(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess features for model training/prediction."""
    df = df.copy()

    # Categorical columns
    categorical_cols = [
        "horse_sex",
        "course_type",
        "venue",
        "track_condition",
        "weather",
        "running_style",
        "workout_evaluation",
    ]

    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    # Numerical columns with their default values
    numerical_defaults = {
        "horse_age": 4,
        "horse_weight": 480,
        "horse_weight_diff": 0,
        "distance": 2000,
        "post_position": 5,
        "horse_number": 5,
        "weight": 55,
        "odds": 10.0,
        "popularity": 8,
        "avg_position_last5": 5.0,
        "win_rate": 0.1,
        "place_rate": 0.3,
        "avg_last_3f": 35.0,
        "best_last_3f": 34.0,
        "days_since_last_race": 30,
        "jockey_win_rate": 0.1,
        "jockey_venue_win_rate": 0.1,
        "escape_horse_count": 1,
        "front_horse_count": 4,
        "is_inner_post": 0,
        "is_outer_post": 0,
        "rest_flag": 0,
        "short_rotation_flag": 0,
        "same_distance_win_rate": 0.1,
        "same_distance_place_rate": 0.3,
        "same_venue_win_rate": 0.1,
        "same_venue_place_rate": 0.3,
        "same_track_condition_place_rate": 0.3,
    }

    for col, default in numerical_defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)

    return df


def get_feature_columns() -> list[str]:
    """Get list of feature columns for model."""
    return [
        # Horse basic info
        "horse_age",
        "horse_sex",
        "horse_weight",
        "horse_weight_diff",
        # Race conditions
        "distance",
        "course_type",
        "venue",
        "track_condition",
        "weather",
        "post_position",
        "horse_number",
        "weight",
        # Post position derived
        "is_inner_post",
        "is_outer_post",
        # Odds
        "odds",
        "popularity",
        # Running style
        "running_style",
        "escape_horse_count",
        "front_horse_count",
        # Past performance
        "avg_position_last5",
        "win_rate",
        "place_rate",
        "avg_last_3f",
        "best_last_3f",
        "days_since_last_race",
        # Rotation derived
        "rest_flag",
        "short_rotation_flag",
        # Aptitude
        "same_distance_win_rate",
        "same_distance_place_rate",
        "same_venue_win_rate",
        "same_venue_place_rate",
        "same_track_condition_place_rate",
        # Jockey
        "jockey_win_rate",
        "jockey_venue_win_rate",
        # Workout
        "workout_evaluation",
    ]


def create_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create derived features from base features."""
    df = df.copy()

    # Post position features
    if "post_position" in df.columns:
        df["is_inner_post"] = (df["post_position"] <= 3).astype(int)
        df["is_outer_post"] = (df["post_position"] >= 6).astype(int)

    # Rotation features
    if "days_since_last_race" in df.columns:
        df["rest_flag"] = (df["days_since_last_race"] >= 70).astype(int)
        df["short_rotation_flag"] = (df["days_since_last_race"] <= 14).astype(int)

    # Odds-based features
    if "odds" in df.columns:
        df["log_odds"] = df["odds"].apply(lambda x: np.log(x) if x > 0 else 0)

    # Weight-based features
    if "weight" in df.columns and "horse_weight" in df.columns:
        df["weight_ratio"] = df["weight"] / df["horse_weight"]

    # Performance trend
    if "avg_position_last5" in df.columns and "win_rate" in df.columns:
        df["form_score"] = (1 / df["avg_position_last5"]) * df["win_rate"]

    # Pace advantage score
    if all(
        col in df.columns
        for col in ["running_style", "escape_horse_count", "front_horse_count"]
    ):

        def calc_pace_advantage(row):
            style = row.get("running_style", "FRONT")
            escape_count = row.get("escape_horse_count", 1)
            front_count = row.get("front_horse_count", 4)

            # High pace favors stalkers/closers
            if escape_count >= 2:
                if style in ["STALKER", "CLOSER"]:
                    return 1.2
                elif style in ["ESCAPE", "FRONT"]:
                    return 0.8
            # Slow pace favors front runners
            elif escape_count <= 1 and front_count <= 3:
                if style in ["ESCAPE", "FRONT"]:
                    return 1.2
                elif style in ["STALKER", "CLOSER"]:
                    return 0.8
            return 1.0

        df["pace_advantage"] = df.apply(calc_pace_advantage, axis=1)

    return df
