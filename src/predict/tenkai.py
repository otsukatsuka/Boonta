"""展開予想 (race development forecast) text formatter."""
from __future__ import annotations

import pandas as pd

# Running style code to name mapping
RUNNING_STYLE_NAMES = {
    1: "逃げ", 2: "先行", 3: "差し", 4: "追込",
}

# Pace forecast to display name
PACE_NAMES = {"H": "ハイ", "M": "ミドル", "S": "スロー"}

# IO position to label
IO_LABELS = {1: "最内", 2: "内", 3: "中", 4: "外", 5: "大外"}


def format_tenkai(
    features_df: pd.DataFrame,
    predictions: list[float] | None = None,
) -> str:
    """Format race development forecast as text.

    Args:
        features_df: Prediction features DataFrame with metadata columns
            (race_key, horse_number, horse_name, plus ML features).
        predictions: Optional list of is_place probabilities (same order as df).

    Returns:
        Formatted text string for terminal output.
    """
    df = features_df.copy()
    if predictions is not None:
        df["predict_prob"] = predictions

    lines: list[str] = []
    lines.append("=" * 50)

    # -- Pace forecast
    pace = _format_pace(df)
    lines.append(pace)
    lines.append("")

    # -- Position table
    pos_table = _format_position_table(df)
    lines.append(pos_table)
    lines.append("")

    # -- ML predictions
    if "predict_prob" in df.columns:
        ml_section = _format_ml_predictions(df)
        lines.append(ml_section)
        lines.append("")

    # -- Advantage/Disadvantage
    adv = _format_advantages(df)
    if adv:
        lines.append(adv)
        lines.append("")

    # -- Upset horses
    upset = _format_upset(df)
    if upset:
        lines.append(upset)

    lines.append("=" * 50)
    return "\n".join(lines)


def _format_pace(df: pd.DataFrame) -> str:
    """Format pace forecast section."""
    lines = []

    # Determine overall pace from distribution
    if "pace_forecast" in df.columns:
        pace_counts = df["pace_forecast"].value_counts()
        dominant = pace_counts.index[0] if len(pace_counts) > 0 else "M"
        pace_label = PACE_NAMES.get(str(dominant), str(dominant))
        lines.append(f"■ ペース予想: {pace_label} ({dominant})")
    else:
        lines.append("■ ペース予想: 不明")

    # Identify front runners
    if "running_style" in df.columns and "horse_number" in df.columns:
        nige = df[df["running_style"].astype(str) == "1"]
        if len(nige) > 0:
            names = _horse_labels(nige)
            lines.append(f"  逃げ馬: {', '.join(names)}")

        senko = df[df["running_style"].astype(str).isin(["1", "2"])]
        if len(senko) > 1:
            names = _horse_labels(senko)
            lines.append(f"  先行争い: {', '.join(names)}")

    return "\n".join(lines)


def _format_position_table(df: pd.DataFrame) -> str:
    """Format position forecast table."""
    lines = ["■ 位置取り予想"]
    header = f"  {'馬番':>4}  {'馬名':<14}  {'脚質':<4}  {'道中':>4}  {'後3F':>4}"
    header += f"  {'ゴール':>4}  {'内外'}"
    lines.append(header)

    sorted_df = df.sort_values("goal_position") if "goal_position" in df.columns else df

    for _, row in sorted_df.head(18).iterrows():
        umaban = int(row.get("horse_number", 0))
        name = str(row.get("horse_name", ""))[:7]
        style = RUNNING_STYLE_NAMES.get(
            int(row.get("running_style", 0)) if pd.notna(row.get("running_style")) else 0,
            "自在"
        )
        mid = int(row["mid_position"]) if pd.notna(row.get("mid_position")) else "-"
        late = int(row["late3f_position"]) if pd.notna(row.get("late3f_position")) else "-"
        goal = int(row["goal_position"]) if pd.notna(row.get("goal_position")) else "-"
        io = IO_LABELS.get(
            int(row["goal_io"]) if pd.notna(row.get("goal_io")) else 0,
            "-"
        )
        lines.append(f"  {umaban:4d}  {name:<14}  {style:<4}  {mid:>4}  {late:>4}  {goal:>4}  {io}")

    return "\n".join(lines)


def _format_ml_predictions(df: pd.DataFrame) -> str:
    """Format ML prediction rankings."""
    lines = ["■ ML予測 (is_place確率)"]

    sorted_df = df.sort_values("predict_prob", ascending=False)
    for rank, (_, row) in enumerate(sorted_df.head(10).iterrows(), 1):
        umaban = int(row.get("horse_number", 0))
        name = str(row.get("horse_name", ""))[:7]
        prob = float(row["predict_prob"]) * 100
        lines.append(f"  {rank:2d}位: {umaban:2d}番 {name:<14} {prob:5.1f}%")

    return "\n".join(lines)


def _format_advantages(df: pd.DataFrame) -> str:
    """Format advantage/disadvantage section."""
    lines = ["■ 有利馬・不利馬"]
    found = False

    # Advantage: low goal_position + inner position
    if "goal_position" in df.columns and "goal_io" in df.columns:
        favorable = df[
            (df["goal_position"] <= 3) &
            (df["goal_io"] <= 2)
        ]
        for _, row in favorable.iterrows():
            label = _horse_label(row)
            style = RUNNING_STYLE_NAMES.get(int(row.get("running_style", 0)), "")
            lines.append(f"  ★有利: {label} ({style} + 内枠)")
            found = True

    # Disadvantage: high gate miss rate
    if "gate_miss_rate" in df.columns:
        risky = df[df["gate_miss_rate"] > 10.0]
        for _, row in risky.iterrows():
            label = _horse_label(row)
            rate = float(row["gate_miss_rate"])
            lines.append(f"  ▲不利: {label} (出遅率{rate:.1f}%)")
            found = True

    return "\n".join(lines) if found else ""


def _format_upset(df: pd.DataFrame) -> str:
    """Format upset horse section."""
    if "upset_index" not in df.columns:
        return ""

    lines = ["■ 穴馬注意"]
    upset = df[df["upset_index"] >= 70].sort_values("upset_index", ascending=False)

    if len(upset) == 0:
        return ""

    for _, row in upset.head(3).iterrows():
        label = _horse_label(row)
        idx = int(row["upset_index"])
        lines.append(f"  {label} (万券指数: {idx})")

    return "\n".join(lines)


def _horse_label(row: pd.Series) -> str:
    """Create '番号番 馬名' label."""
    umaban = int(row.get("horse_number", 0))
    name = str(row.get("horse_name", ""))
    return f"{umaban}番 {name}"


def _horse_labels(df: pd.DataFrame) -> list[str]:
    """Create list of horse labels."""
    return [_horse_label(row) for _, row in df.iterrows()]
