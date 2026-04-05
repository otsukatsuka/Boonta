"""Feature engineering pipeline: KYI/SED DataFrames → ML-ready features."""
from __future__ import annotations

import pandas as pd

from src.features.columns import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    FIELD_TO_FEATURE,
    LABEL_COLUMN,
    NUMERICAL_DEFAULTS,
)
from src.features.derived import add_derived_features
from src.parser.engine import build_race_key


def _add_race_key(df: pd.DataFrame) -> pd.DataFrame:
    """Add race_key column to a parsed JRDB DataFrame."""
    df = df.copy()
    df["race_key"] = df.apply(
        lambda row: build_race_key(row.to_dict()), axis=1
    )
    return df


def _rename_to_features(df: pd.DataFrame) -> pd.DataFrame:
    """Rename JRDB field names to ML feature names."""
    rename_map = {k: v for k, v in FIELD_TO_FEATURE.items() if k in df.columns}
    return df.rename(columns=rename_map)


def _convert_weight(df: pd.DataFrame) -> pd.DataFrame:
    """Convert weight_carried from 0.1kg units to kg."""
    df = df.copy()
    if "weight_carried" in df.columns:
        df["weight_carried"] = pd.to_numeric(df["weight_carried"], errors="coerce") / 10.0
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing values and cast types for ML features.

    Args:
        df: DataFrame with ML feature column names.

    Returns:
        Preprocessed DataFrame.
    """
    df = df.copy()

    # Fill categorical with "Unknown"
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)

    # Fill numerical with defaults
    for col, default in NUMERICAL_DEFAULTS.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)

    return df


def build_training_features(
    kyi_df: pd.DataFrame,
    sed_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build training features from KYI (predictions) and SED (results).

    KYI provides input features (available at prediction time).
    SED provides the label (is_place = 着順 <= 3) and anomaly filters.

    Args:
        kyi_df: Parsed KYI DataFrame (from parse_file).
        sed_df: Parsed SED DataFrame (from parse_file).

    Returns:
        DataFrame with FEATURE_COLUMNS + is_place label.
    """
    # Add race keys for joining
    kyi = _add_race_key(kyi_df)
    sed = _add_race_key(sed_df)

    # Rename to feature names
    kyi = _rename_to_features(kyi)
    sed = _rename_to_features(sed)

    # Convert weight
    kyi = _convert_weight(kyi)

    # Join on race_key + horse_number
    merged = kyi.merge(
        sed[["race_key", "horse_number", "着順", "異常区分"]].rename(
            columns={"馬番": "horse_number"}
        ) if "馬番" in sed.columns else sed[["race_key", "horse_number", "着順", "異常区分"]],
        on=["race_key", "horse_number"],
        how="inner",
        suffixes=("", "_sed"),
    )

    # Filter out anomalies (取消, 失格, etc.)
    if "異常区分" in merged.columns:
        merged = merged[
            (merged["異常区分"].isna()) | (merged["異常区分"] == 0)
        ].copy()

    # Create is_place label
    merged[LABEL_COLUMN] = (merged["着順"] <= 3).astype(int)

    # Add derived features
    merged = add_derived_features(merged)

    # Preprocess
    merged = preprocess(merged)

    # Select only feature columns + label
    available = [c for c in FEATURE_COLUMNS if c in merged.columns]
    result = merged[available + [LABEL_COLUMN]].copy()

    return result


def build_prediction_features(kyi_df: pd.DataFrame) -> pd.DataFrame:
    """Build prediction features from KYI data only.

    Args:
        kyi_df: Parsed KYI DataFrame.

    Returns:
        DataFrame with FEATURE_COLUMNS (no label).
    """
    kyi = _add_race_key(kyi_df)
    kyi = _rename_to_features(kyi)
    kyi = _convert_weight(kyi)
    kyi = add_derived_features(kyi)
    kyi = preprocess(kyi)

    # Keep metadata columns for output formatting
    meta_cols = ["race_key", "horse_number"]
    if "馬名" in kyi_df.columns:
        kyi["horse_name"] = kyi_df["馬名"]
        meta_cols.append("horse_name")

    available = [c for c in FEATURE_COLUMNS if c in kyi.columns]
    keep_meta = [c for c in meta_cols if c in kyi.columns]

    return kyi[keep_meta + available].copy()
