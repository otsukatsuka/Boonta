"""ROI (Return on Investment) evaluation using HJC payoff data."""
from __future__ import annotations

import pandas as pd


def evaluate_roi(
    predictions_df: pd.DataFrame,
    hjc_df: pd.DataFrame,
    strategy: str = "fukusho_top3",
) -> dict:
    """Evaluate ROI by comparing predictions against actual payoffs.

    Args:
        predictions_df: DataFrame with columns: race_key, horse_number, predict_prob.
        hjc_df: Parsed HJC DataFrame with payoff columns.
        strategy: Betting strategy. One of:
            - "fukusho_top3": Place bet on top 3 predicted horses (100 yen each)
            - "umaren_top2": Quinella on top 2 predicted horses (100 yen)
            - "sanrenpuku_top3": Trifecta on top 3 predicted horses (100 yen)

    Returns:
        Dict with total_bets, total_return, roi, hit_count, race_count, details.
    """
    strategies = {
        "fukusho_top3": _evaluate_fukusho,
        "umaren_top2": _evaluate_umaren,
        "sanrenpuku_top3": _evaluate_sanrenpuku,
    }

    if strategy not in strategies:
        raise ValueError(f"Unknown strategy: {strategy}. Must be one of {list(strategies)}")

    return strategies[strategy](predictions_df, hjc_df)


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
