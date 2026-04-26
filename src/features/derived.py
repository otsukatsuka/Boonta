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

    # Race-relative features (per-race rank, z-score, odds share)
    df = add_race_relative_features(df)

    return df


# Indices that get per-race rank + z-score
_RACE_RELATIVE_SPECS: list[tuple[str, str, str]] = [
    ("idm", "idm_rank_in_race", "idm_z_in_race"),
    ("overall_index", "overall_rank_in_race", "overall_z_in_race"),
    ("jockey_index", "jockey_rank_in_race", "jockey_z_in_race"),
    ("ten_index", "ten_rank_in_race", "ten_z_in_race"),
    ("agari_index", "agari_rank_in_race", "agari_z_in_race"),
    ("position_index", "position_rank_in_race", "position_z_in_race"),
]


def add_race_relative_features(df: pd.DataFrame) -> pd.DataFrame:
    """Per-race rank and z-score for major indices, plus odds share.

    Requires ``race_key`` column. If missing, returns ``df`` unchanged so the
    later preprocess step fills race-relative columns with NUMERICAL_DEFAULTS.

    For each index in :data:`_RACE_RELATIVE_SPECS`:
      - ``{name}_rank_in_race``: descending rank (highest index = 1)
      - ``{name}_z_in_race``: z-score within the race

    Plus:
      - ``odds_share``: ``(1/odds_i) / Σ(1/odds_j)`` — market-implied probability
      - ``popularity_z_in_race``: z-score of basis popularity
    """
    if "race_key" not in df.columns:
        return df

    df = df.copy()
    groups = df["race_key"]

    for src_col, rank_col, z_col in _RACE_RELATIVE_SPECS:
        if src_col not in df.columns:
            continue
        series = pd.to_numeric(df[src_col], errors="coerce")
        df[rank_col] = series.groupby(groups).rank(ascending=False, method="min")
        mean = series.groupby(groups).transform("mean")
        std = series.groupby(groups).transform("std").replace(0, np.nan)
        df[z_col] = (series - mean) / std

    if "odds" in df.columns:
        odds = pd.to_numeric(df["odds"], errors="coerce").clip(lower=1.0)
        inv = 1.0 / odds
        total = inv.groupby(groups).transform("sum")
        df["odds_share"] = inv / total

    if "popularity" in df.columns:
        pop = pd.to_numeric(df["popularity"], errors="coerce")
        mean = pop.groupby(groups).transform("mean")
        std = pop.groupby(groups).transform("std").replace(0, np.nan)
        df["popularity_z_in_race"] = (pop - mean) / std

    return df
