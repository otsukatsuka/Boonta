"""ROI (Return on Investment) evaluation using HJC payoff data."""
from __future__ import annotations

from itertools import combinations

import pandas as pd


def evaluate_roi(
    predictions_df: pd.DataFrame,
    hjc_df: pd.DataFrame,
    strategy: str = "fukusho_top3",
    ev_threshold: float = 1.0,
) -> dict:
    """Evaluate ROI by comparing predictions against actual payoffs.

    Args:
        predictions_df: DataFrame with columns: race_key, horse_number, predict_prob.
            For EV-based strategies, must also include: odds, fukusho_odds.
        hjc_df: Parsed HJC DataFrame with payoff columns.
        strategy: Betting strategy. One of:
            - "fukusho_top3": Place bet on top 3 predicted horses (100 yen each)
            - "umaren_top2": Quinella on top 2 predicted horses (100 yen)
            - "sanrenpuku_top3": Trifecta on top 3 predicted horses (100 yen)
            - "ev_tansho": Win bet on horses with ev_tan > threshold (100 yen each)
            - "ev_fukusho": Place bet on horses with ev_fuku > threshold (100 yen each)
            - "ev_sanrenpuku_nagashi": 3連複1頭流し per axis (ev_fuku > threshold)
              with 5 partners by ev_tan (10 combos × 100 yen per axis)
        ev_threshold: Minimum expected value for EV-based strategies.

    Returns:
        Dict with total_bets, total_return, roi, hit_count, race_count, details.
        EV strategies additionally include bet_race_count and ev_threshold.
    """
    if strategy == "fukusho_top3":
        return _evaluate_fukusho(predictions_df, hjc_df)
    if strategy == "umaren_top2":
        return _evaluate_umaren(predictions_df, hjc_df)
    if strategy == "sanrenpuku_top3":
        return _evaluate_sanrenpuku(predictions_df, hjc_df)
    if strategy == "ev_tansho":
        return _evaluate_ev_tansho(predictions_df, hjc_df, ev_threshold)
    if strategy == "ev_fukusho":
        return _evaluate_ev_fukusho(predictions_df, hjc_df, ev_threshold)
    if strategy == "ev_sanrenpuku_nagashi":
        return _evaluate_ev_sanrenpuku_nagashi(predictions_df, hjc_df, ev_threshold)

    valid = [
        "fukusho_top3", "umaren_top2", "sanrenpuku_top3",
        "ev_tansho", "ev_fukusho", "ev_sanrenpuku_nagashi",
    ]
    raise ValueError(f"Unknown strategy: {strategy}. Must be one of {valid}")


def _compute_race_ev(race_group: pd.DataFrame) -> pd.DataFrame:
    """Attach ev_tan and ev_fuku columns. Mirrors src.predict.betting formulas."""
    df = race_group.copy()
    df["odds"] = pd.to_numeric(df.get("odds"), errors="coerce")
    df["fukusho_odds"] = pd.to_numeric(df.get("fukusho_odds"), errors="coerce")
    df["ev_tan"] = (df["predict_prob"] / 3.0) * df["odds"]
    df["ev_fuku"] = df["predict_prob"] * df["fukusho_odds"]
    return df


def _get_top_horses(predictions_df: pd.DataFrame, n: int) -> dict[str, list[int]]:
    """Get top N predicted horses per race.

    Returns:
        Dict mapping race_key to list of horse_numbers (sorted by probability desc).
    """
    result = {}
    for race_key, group in predictions_df.groupby("race_key"):
        sorted_group = group.sort_values("predict_prob", ascending=False)
        top = sorted_group["horse_number"].head(n).tolist()
        result[str(race_key)] = [int(h) for h in top]
    return result


def _evaluate_fukusho(predictions_df: pd.DataFrame, hjc_df: pd.DataFrame) -> dict:
    """Evaluate 複勝 (place) betting on top 3 predicted horses."""
    top_horses = _get_top_horses(predictions_df, 3)

    total_bets = 0
    total_return = 0
    hit_count = 0
    race_count = 0
    details = []

    for race_key, horses in top_horses.items():
        hjc_race = hjc_df[hjc_df["race_key"] == race_key]
        if len(hjc_race) == 0:
            continue

        race_count += 1
        row = hjc_race.iloc[0]

        # Get place payoff horse numbers and amounts
        place_winners = {}
        for i in range(1, 6):
            umaban = row.get(f"複勝馬番_{i}")
            payout = row.get(f"複勝払戻_{i}")
            if pd.notna(umaban) and umaban and int(umaban) > 0:
                place_winners[int(umaban)] = int(payout) if pd.notna(payout) else 0

        race_bets = len(horses) * 100  # 100 yen per horse
        race_return = 0

        for horse in horses:
            total_bets += 100
            if horse in place_winners:
                total_return += place_winners[horse]
                race_return += place_winners[horse]
                hit_count += 1

        details.append({
            "race_key": race_key,
            "bet_horses": horses,
            "bets": race_bets,
            "return": race_return,
            "hit": race_return > 0,
        })

    roi = (total_return / total_bets * 100) if total_bets > 0 else 0.0

    return {
        "strategy": "fukusho_top3",
        "total_bets": total_bets,
        "total_return": total_return,
        "roi": round(roi, 1),
        "hit_count": hit_count,
        "race_count": race_count,
        "details": details,
    }


def _evaluate_umaren(predictions_df: pd.DataFrame, hjc_df: pd.DataFrame) -> dict:
    """Evaluate 馬連 (quinella) betting on top 2 predicted horses."""
    top_horses = _get_top_horses(predictions_df, 2)

    total_bets = 0
    total_return = 0
    hit_count = 0
    race_count = 0
    details = []

    for race_key, horses in top_horses.items():
        if len(horses) < 2:
            continue

        hjc_race = hjc_df[hjc_df["race_key"] == race_key]
        if len(hjc_race) == 0:
            continue

        race_count += 1
        row = hjc_race.iloc[0]
        total_bets += 100

        bet_combo = set(horses[:2])
        race_return = 0

        for i in range(1, 4):
            combo_str = str(row.get(f"馬連組合せ_{i}", "")).strip()
            payout = row.get(f"馬連払戻_{i}")
            if combo_str and len(combo_str) == 4:
                h1 = int(combo_str[:2])
                h2 = int(combo_str[2:])
                if {h1, h2} == bet_combo and pd.notna(payout) and int(payout) > 0:
                    race_return = int(payout)
                    total_return += race_return
                    hit_count += 1
                    break

        details.append({
            "race_key": race_key,
            "bet_horses": horses[:2],
            "bets": 100,
            "return": race_return,
            "hit": race_return > 0,
        })

    roi = (total_return / total_bets * 100) if total_bets > 0 else 0.0

    return {
        "strategy": "umaren_top2",
        "total_bets": total_bets,
        "total_return": total_return,
        "roi": round(roi, 1),
        "hit_count": hit_count,
        "race_count": race_count,
        "details": details,
    }


def _evaluate_sanrenpuku(predictions_df: pd.DataFrame, hjc_df: pd.DataFrame) -> dict:
    """Evaluate 3連複 (trifecta) betting on top 3 predicted horses."""
    top_horses = _get_top_horses(predictions_df, 3)

    total_bets = 0
    total_return = 0
    hit_count = 0
    race_count = 0
    details = []

    for race_key, horses in top_horses.items():
        if len(horses) < 3:
            continue

        hjc_race = hjc_df[hjc_df["race_key"] == race_key]
        if len(hjc_race) == 0:
            continue

        race_count += 1
        row = hjc_race.iloc[0]
        total_bets += 100

        bet_combo = set(horses[:3])
        race_return = 0

        for i in range(1, 4):
            combo_str = str(row.get(f"三連複組合せ_{i}", "")).strip()
            payout = row.get(f"三連複払戻_{i}")
            if combo_str and len(combo_str) == 6:
                h1 = int(combo_str[:2])
                h2 = int(combo_str[2:4])
                h3 = int(combo_str[4:6])
                if {h1, h2, h3} == bet_combo and pd.notna(payout) and int(payout) > 0:
                    race_return = int(payout)
                    total_return += race_return
                    hit_count += 1
                    break

        details.append({
            "race_key": race_key,
            "bet_horses": horses[:3],
            "bets": 100,
            "return": race_return,
            "hit": race_return > 0,
        })

    roi = (total_return / total_bets * 100) if total_bets > 0 else 0.0

    return {
        "strategy": "sanrenpuku_top3",
        "total_bets": total_bets,
        "total_return": total_return,
        "roi": round(roi, 1),
        "hit_count": hit_count,
        "race_count": race_count,
        "details": details,
    }


def _evaluate_ev_tansho(
    predictions_df: pd.DataFrame,
    hjc_df: pd.DataFrame,
    ev_threshold: float,
) -> dict:
    """Evaluate 単勝 betting on horses with ev_tan > threshold (100 yen each)."""
    total_bets = 0
    total_return = 0
    hit_count = 0
    race_count = 0
    bet_race_count = 0
    details = []

    for race_key, group in predictions_df.groupby("race_key"):
        hjc_race = hjc_df[hjc_df["race_key"] == race_key]
        if len(hjc_race) == 0:
            continue

        race_count += 1
        ev = _compute_race_ev(group)
        picks = ev[ev["ev_tan"] > ev_threshold]
        horses = [int(h) for h in picks["horse_number"].tolist()]

        if not horses:
            details.append({
                "race_key": str(race_key), "bet_horses": [],
                "bets": 0, "return": 0, "hit": False,
            })
            continue

        row = hjc_race.iloc[0]
        win_payouts: dict[int, int] = {}
        for i in range(1, 4):
            umaban = row.get(f"単勝馬番_{i}")
            payout = row.get(f"単勝払戻_{i}")
            if pd.notna(umaban) and umaban and int(umaban) > 0:
                win_payouts[int(umaban)] = int(payout) if pd.notna(payout) else 0

        race_bets = len(horses) * 100
        race_return = 0
        race_hits = 0
        for horse in horses:
            if horse in win_payouts:
                race_return += win_payouts[horse]
                race_hits += 1

        total_bets += race_bets
        total_return += race_return
        hit_count += race_hits
        bet_race_count += 1

        details.append({
            "race_key": str(race_key), "bet_horses": horses,
            "bets": race_bets, "return": race_return, "hit": race_return > 0,
        })

    roi = (total_return / total_bets * 100) if total_bets > 0 else 0.0

    return {
        "strategy": "ev_tansho",
        "ev_threshold": ev_threshold,
        "total_bets": total_bets,
        "total_return": total_return,
        "roi": round(roi, 1),
        "hit_count": hit_count,
        "race_count": race_count,
        "bet_race_count": bet_race_count,
        "details": details,
    }


def _evaluate_ev_fukusho(
    predictions_df: pd.DataFrame,
    hjc_df: pd.DataFrame,
    ev_threshold: float,
) -> dict:
    """Evaluate 複勝 betting on horses with ev_fuku > threshold (100 yen each)."""
    total_bets = 0
    total_return = 0
    hit_count = 0
    race_count = 0
    bet_race_count = 0
    details = []

    for race_key, group in predictions_df.groupby("race_key"):
        hjc_race = hjc_df[hjc_df["race_key"] == race_key]
        if len(hjc_race) == 0:
            continue

        race_count += 1
        ev = _compute_race_ev(group)
        picks = ev[ev["ev_fuku"] > ev_threshold]
        horses = [int(h) for h in picks["horse_number"].tolist()]

        if not horses:
            details.append({
                "race_key": str(race_key), "bet_horses": [],
                "bets": 0, "return": 0, "hit": False,
            })
            continue

        row = hjc_race.iloc[0]
        place_payouts: dict[int, int] = {}
        for i in range(1, 6):
            umaban = row.get(f"複勝馬番_{i}")
            payout = row.get(f"複勝払戻_{i}")
            if pd.notna(umaban) and umaban and int(umaban) > 0:
                place_payouts[int(umaban)] = int(payout) if pd.notna(payout) else 0

        race_bets = len(horses) * 100
        race_return = 0
        race_hits = 0
        for horse in horses:
            if horse in place_payouts:
                race_return += place_payouts[horse]
                race_hits += 1

        total_bets += race_bets
        total_return += race_return
        hit_count += race_hits
        bet_race_count += 1

        details.append({
            "race_key": str(race_key), "bet_horses": horses,
            "bets": race_bets, "return": race_return, "hit": race_return > 0,
        })

    roi = (total_return / total_bets * 100) if total_bets > 0 else 0.0

    return {
        "strategy": "ev_fukusho",
        "ev_threshold": ev_threshold,
        "total_bets": total_bets,
        "total_return": total_return,
        "roi": round(roi, 1),
        "hit_count": hit_count,
        "race_count": race_count,
        "bet_race_count": bet_race_count,
        "details": details,
    }


def _evaluate_ev_sanrenpuku_nagashi(
    predictions_df: pd.DataFrame,
    hjc_df: pd.DataFrame,
    ev_threshold: float,
) -> dict:
    """Evaluate 3連複1頭流し per EV complex axis, top-5 ev_tan partners."""
    total_bets = 0
    total_return = 0
    hit_count = 0
    race_count = 0
    bet_race_count = 0
    details = []

    for race_key, group in predictions_df.groupby("race_key"):
        hjc_race = hjc_df[hjc_df["race_key"] == race_key]
        if len(hjc_race) == 0:
            continue

        race_count += 1
        ev = _compute_race_ev(group)
        ev = ev.assign(horse_number=ev["horse_number"].astype(int))

        axes = ev[ev["ev_fuku"] > ev_threshold]["horse_number"].tolist()
        if not axes:
            details.append({
                "race_key": str(race_key), "axes": [], "combos": 0,
                "bets": 0, "return": 0, "hit": False,
            })
            continue

        row = hjc_race.iloc[0]
        winning_sets: list[tuple[frozenset, int]] = []
        for i in range(1, 4):
            combo_str = str(row.get(f"三連複組合せ_{i}", "")).strip()
            payout = row.get(f"三連複払戻_{i}")
            if len(combo_str) == 6 and pd.notna(payout) and int(payout) > 0:
                winning_sets.append((
                    frozenset({
                        int(combo_str[:2]),
                        int(combo_str[2:4]),
                        int(combo_str[4:6]),
                    }),
                    int(payout),
                ))

        race_bets = 0
        race_return = 0
        race_hits = 0
        axes_used = []

        for axis in axes:
            partners = (
                ev[ev["horse_number"] != axis]
                .sort_values("ev_tan", ascending=False)
                .head(5)["horse_number"]
                .tolist()
            )
            if len(partners) < 5:
                continue

            axes_used.append(axis)
            combos = [frozenset((axis, a, b)) for a, b in combinations(partners, 2)]
            race_bets += 100 * len(combos)

            for win_set, payout in winning_sets:
                if win_set in combos:
                    race_return += payout
                    race_hits += 1
                    break

        if race_bets > 0:
            bet_race_count += 1
        total_bets += race_bets
        total_return += race_return
        hit_count += race_hits

        details.append({
            "race_key": str(race_key),
            "axes": axes_used,
            "combos": race_bets // 100,
            "bets": race_bets,
            "return": race_return,
            "hit": race_return > 0,
        })

    roi = (total_return / total_bets * 100) if total_bets > 0 else 0.0

    return {
        "strategy": "ev_sanrenpuku_nagashi",
        "ev_threshold": ev_threshold,
        "total_bets": total_bets,
        "total_return": total_return,
        "roi": round(roi, 1),
        "hit_count": hit_count,
        "race_count": race_count,
        "bet_race_count": bet_race_count,
        "details": details,
    }
