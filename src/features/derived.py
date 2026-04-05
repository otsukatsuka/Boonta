"""Derived feature calculations."""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features to a DataFrame that already has base features.

    Args:
        df: DataFrame with base feature columns.

    Returns:
        DataFrame with derived columns added.
    """
    df = df.copy()

    # speed_balance: positive = front-runner type, negative = closer type
    if "ten_index" in df.columns and "agari_index" in df.columns:
        df["speed_balance"] = df["ten_index"] - df["agari_index"]

    # position_delta: negative = gaining positions, positive = losing
    if "goal_position" in df.columns and "mid_position" in df.columns:
        df["position_delta"] = df["goal_position"] - df["mid_position"]

    # io_shift: inside/outside movement through the race
    if "goal_io" in df.columns and "mid_position_io" in df.columns:
        df["io_shift"] = df["goal_io"] - df["mid_position_io"]

    # log_odds: log transform of odds for better distribution
    if "odds" in df.columns:
        df["log_odds"] = np.log(df["odds"].clip(lower=1.0))

    # risk_score: gate miss risk
    if "gate_miss_rate" in df.columns and "start_index" in df.columns:
        df["risk_score"] = df["gate_miss_rate"] * (1 - df["start_index"] / 10)

    # race_head_count: number of horses per race
    if "race_key" in df.columns:
        df["race_head_count"] = df.groupby("race_key")["race_key"].transform("count")
    elif "horse_number" in df.columns:
        # Fallback: use max horse_number as proxy
        df["race_head_count"] = 16  # default

    return df
