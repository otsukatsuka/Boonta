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


def _parse_body_weight_delta(df: pd.DataFrame) -> pd.DataFrame:
    """Parse 枠確定馬体重増減 (e.g. '+05', '-08', '   ') into signed kg.

    JRDB stores the delta as a 3-char string: sign + 2-digit magnitude.
    Empty/whitespace is treated as missing → 0.0 (handled later by defaults).
    """
    df = df.copy()
    src = df.get("枠確定馬体重増減")
    if src is None:
        return df

    def _to_signed(val: object) -> float | None:
        if val is None:
            return None
        s = str(val).strip()
        if not s or s in {"+", "-", "***"}:
            return None
        sign = -1.0 if s.startswith("-") else 1.0
        digits = "".join(ch for ch in s if ch.isdigit())
        if not digits:
            return None
        return sign * float(digits)

    df["body_weight_delta"] = src.map(_to_signed)
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

    # Parse body_weight_delta before renaming (uses raw JRDB column name)
    kyi = _parse_body_weight_delta(kyi)

    # Rename to feature names
    kyi = _rename_to_features(kyi)
    sed = _rename_to_features(sed)

    # Convert weight
    kyi = _convert_weight(kyi)

    # Join on race_key + horse_number
    # After _rename_to_features(), 馬番 is already horse_number in both DFs.
    # SED: 着順 (label) and 異常区分 (filter) are not in FIELD_TO_FEATURE.
    sed_cols = ["race_key", "horse_number"]
    if "着順" in sed.columns:
        sed_cols.append("着順")
    if "異常区分" in sed.columns:
        sed_cols.append("異常区分")

    merged = kyi.merge(
        sed[sed_cols],
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

    # Phase 2: keep raw finish_order for lambdarank labels
    merged["finish_order"] = pd.to_numeric(merged["着順"], errors="coerce")

    # Add derived features
    merged = add_derived_features(merged)

    # Preprocess
    merged = preprocess(merged)

    # Select feature columns + label + race_key + finish_order
    # race_key / finish_order are preserved so Modal can compute per-race metrics
    # (Hit@3 etc.) and lambdarank labels. Both are passed to AutoGluon via
    # ignored_columns to avoid using them as features.
    available = [c for c in FEATURE_COLUMNS if c in merged.columns]
    keep = available + [LABEL_COLUMN]
    if "finish_order" in merged.columns:
        keep = ["finish_order"] + keep
    if "race_key" in merged.columns:
        keep = ["race_key"] + keep
    result = merged[keep].copy()

    return result


def build_prediction_features(kyi_df: pd.DataFrame) -> pd.DataFrame:
    """Build prediction features from KYI data only.

    Args:
        kyi_df: Parsed KYI DataFrame.

    Returns:
        DataFrame with FEATURE_COLUMNS (no label).
    """
    kyi = _add_race_key(kyi_df)
    kyi = _parse_body_weight_delta(kyi)
    kyi = _rename_to_features(kyi)
    kyi = _convert_weight(kyi)
    kyi = add_derived_features(kyi)
    kyi = preprocess(kyi)

    # Keep metadata columns for output formatting
    meta_cols = ["race_key", "horse_number"]
    if "馬名" in kyi_df.columns:
        kyi["horse_name"] = kyi_df["馬名"]
        meta_cols.append("horse_name")
    if "基準複勝オッズ" in kyi_df.columns:
        kyi["fukusho_odds"] = pd.to_numeric(kyi_df["基準複勝オッズ"], errors="coerce")
        meta_cols.append("fukusho_odds")

    available = [c for c in FEATURE_COLUMNS if c in kyi.columns]
    keep_meta = [c for c in meta_cols if c in kyi.columns]

    # Avoid duplicate columns (horse_number is in both meta and features)
    all_cols = list(dict.fromkeys(keep_meta + available))
    return kyi[all_cols].copy()
