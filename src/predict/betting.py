"""Expected-value based betting recommendation.

Policy: prioritize ROI (expected value) over hit rate. A horse/bet is a
candidate only when the product of predicted probability and odds exceeds a
threshold (1.0 by default = break-even at the quoted odds).
"""
from __future__ import annotations

from itertools import combinations

import pandas as pd


def compute_expected_values(
    race_df: pd.DataFrame,
    predictions: list[float],
) -> pd.DataFrame:
    """Compute single-win and place expected values per horse.

    The model produces ``is_place`` (top-3) probability, which maps directly to
    the place bet payoff. For the win bet we approximate ``P(win)`` by
    ``is_place / 3`` — on average, one of the three placing horses wins, so
    this is a reasonable first-order estimate until a dedicated win model
    exists.

    Args:
        race_df: Single-race features with columns
            ``horse_number``, ``horse_name`` (optional), ``odds`` (単勝),
            ``fukusho_odds`` (optional).
        predictions: ``is_place`` probabilities aligned with ``race_df`` rows.

    Returns:
        DataFrame sorted by ``ev_tan`` descending with columns
        ``horse_number, horse_name, prob, odds, fukusho_odds, ev_tan, ev_fuku``.
    """
    df = race_df.copy()
    df["prob"] = predictions
    df["odds"] = pd.to_numeric(df.get("odds"), errors="coerce")
    if "fukusho_odds" in df.columns:
        df["fukusho_odds"] = pd.to_numeric(df["fukusho_odds"], errors="coerce")
    else:
        df["fukusho_odds"] = pd.NA

    df["ev_tan"] = (df["prob"] / 3.0) * df["odds"]
    df["ev_fuku"] = df["prob"] * df["fukusho_odds"]

    cols = ["horse_number", "horse_name", "prob", "odds", "fukusho_odds",
            "ev_tan", "ev_fuku"]
    available = [c for c in cols if c in df.columns]
    return df[available].sort_values("ev_tan", ascending=False).reset_index(drop=True)


def recommend_bets(
    ev_df: pd.DataFrame,
    ev_threshold: float = 1.0,
    max_tan: int = 5,
    box_size: int = 3,
    trifecta_box_size: int = 4,
) -> dict:
    """Build EV-driven bet recommendations.

    Strategies:
      - **tansho**: horses whose ``ev_tan > threshold`` (up to ``max_tan``)
      - **fukusho**: horses whose ``ev_fuku > threshold``
      - **umaren_box**: box quinella on top ``box_size`` by ``ev_tan``
      - **sanrenpuku_box**: box trifecta on top ``trifecta_box_size`` by ``ev_tan``

    Args:
        ev_df: Output of :func:`compute_expected_values`.
        ev_threshold: Minimum EV for tan/fuku inclusion.
        max_tan: Cap on tansho picks even if more cross the threshold.
        box_size: Horses in umaren box.
        trifecta_box_size: Horses in sanrenpuku box.

    Returns:
        Dict with keys ``tansho``, ``fukusho``, ``umaren_box``, ``sanrenpuku_box``
        each mapping to a list (horses or tuples).
    """
    if ev_df.empty:
        return {"tansho": [], "fukusho": [], "umaren_box": [], "sanrenpuku_box": []}

    tan_candidates = ev_df[ev_df["ev_tan"] > ev_threshold]
    tansho = tan_candidates.head(max_tan)["horse_number"].astype(int).tolist()

    if "ev_fuku" in ev_df.columns:
        fuku_candidates = ev_df[ev_df["ev_fuku"] > ev_threshold]
        fukusho = fuku_candidates["horse_number"].astype(int).tolist()
    else:
        fukusho = []

    top_tan = ev_df.head(box_size)["horse_number"].astype(int).tolist()
    umaren_box = list(combinations(sorted(top_tan), 2)) if len(top_tan) >= 2 else []

    top_trifecta = ev_df.head(trifecta_box_size)["horse_number"].astype(int).tolist()
    sanrenpuku_box = (
        list(combinations(sorted(top_trifecta), 3)) if len(top_trifecta) >= 3 else []
    )

    return {
        "tansho": tansho,
        "fukusho": fukusho,
        "umaren_box": umaren_box,
        "sanrenpuku_box": sanrenpuku_box,
    }


def recommend_nagashi(
    ev_df: pd.DataFrame,
    axis_criteria: str = "ev_fuku",
    axis_threshold: float = 1.0,
    partner_criteria: str = "ev_tan",
    max_partners: int = 5,
) -> dict:
    """軸1頭流し 買い目生成.

    Pick the highest-ranked horse on ``axis_criteria`` whose value clears
    ``axis_threshold`` as the axis. Take the top ``max_partners`` horses on
    ``partner_criteria`` (excluding the axis) as partners. Combine into 3連複
    (axis + 2 partners). If no horse clears the axis threshold, return
    ``axis=None`` to signal "do not bet".

    Args:
        ev_df: Output of :func:`compute_expected_values`.
        axis_criteria: Column to rank axis candidates ("ev_fuku" or "prob").
        axis_threshold: Minimum ``axis_criteria`` value to qualify as axis.
        partner_criteria: Column to rank partner candidates ("ev_tan" etc.).
        max_partners: Maximum number of partner horses.

    Returns:
        Dict with keys ``axis`` (int|None), ``partners`` (list[int]),
        ``combos`` (list[tuple[int,int,int]] sorted ascending).
    """
    empty: dict = {"axis": None, "partners": [], "combos": []}
    if ev_df.empty or axis_criteria not in ev_df.columns:
        return empty

    axis_candidates = ev_df[ev_df[axis_criteria] > axis_threshold]
    axis_candidates = axis_candidates.sort_values(axis_criteria, ascending=False)
    if axis_candidates.empty:
        return empty

    axis = int(axis_candidates.iloc[0]["horse_number"])

    if partner_criteria not in ev_df.columns:
        return {"axis": axis, "partners": [], "combos": []}

    partner_pool = ev_df[ev_df["horse_number"].astype(int) != axis]
    partner_pool = partner_pool.sort_values(partner_criteria, ascending=False)
    partners = partner_pool.head(max_partners)["horse_number"].astype(int).tolist()

    combos = [
        tuple(sorted((axis, *pair))) for pair in combinations(partners, 2)
    ]

    return {"axis": axis, "partners": partners, "combos": combos}
