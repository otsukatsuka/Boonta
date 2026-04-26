"""Multi-bet EV calculation using Plackett-Luce probabilities.

Bet types supported:
  - **tan**     単勝   = P(win_i) × odds_tan_i
  - **fuku**    複勝   = P(top3_i) × odds_fuku_i
  - **wide**    ワイド = P({i,j} ⊂ top3) × odds_wide_{ij}
  - **umatan**  馬単   = P(i=1, j=2) × odds_umatan_{ij}
  - **sanrenpuku** 三連複 = P({i,j,k} = top3) × odds_sanrenpuku_{ijk}

Source probabilities:
  - ``prob_win``  : P(i is 1st) — from LightGBM lambdarank + softmax (Phase 2).
  - ``prob_top3`` : P(i is in top 3) — from AutoGluon binary (Phase 1).

Plackett-Luce parameters: ``v_i = prob_win_i``. We enumerate orderings to
compute joint top-k probabilities. With N ≤ 18 horses this is fast enough.
"""
from __future__ import annotations

from itertools import combinations, permutations

import numpy as np


def _check_horses(horse_numbers: list[int], prob_win: list[float]) -> None:
    if len(horse_numbers) != len(prob_win):
        raise ValueError(
            f"horse_numbers and prob_win must align: "
            f"{len(horse_numbers)} vs {len(prob_win)}"
        )


def _pl_v(prob_win: list[float]) -> np.ndarray:
    """Plackett-Luce parameters from win probabilities. Drops zero / NaN."""
    v = np.asarray(prob_win, dtype=float)
    v = np.where(np.isfinite(v) & (v > 0), v, 0.0)
    return v


# ----- Joint probabilities -----

def prob_pair_top1_2(prob_win: list[float], i: int, j: int) -> float:
    """P(horse i is 1st and horse j is 2nd) under Plackett-Luce."""
    v = _pl_v(prob_win)
    if i < 0 or j < 0 or i >= len(v) or j >= len(v) or i == j:
        return 0.0
    S = float(v.sum())
    if S <= 0:
        return 0.0
    denom = S - v[i]
    if denom <= 0:
        return 0.0
    return float((v[i] / S) * (v[j] / denom))


def prob_unordered_top2(prob_win: list[float], i: int, j: int) -> float:
    """P({i,j} are 1st and 2nd in either order)."""
    return prob_pair_top1_2(prob_win, i, j) + prob_pair_top1_2(prob_win, j, i)


def prob_pair_in_top3(prob_win: list[float], i: int, j: int) -> float:
    """P(both i and j are in the top-3 finishers).

    Enumerates the 3 ordered positions × the other-horse identity.
    O(N) per pair.
    """
    v = _pl_v(prob_win)
    n = len(v)
    if i < 0 or j < 0 or i >= n or j >= n or i == j:
        return 0.0
    S = float(v.sum())
    if S <= 0:
        return 0.0

    p = 0.0
    # Sum over orderings (a, b, c) of (i, j, *other*) at positions 1, 2, 3.
    pair_orderings = [(i, j), (j, i)]  # (1st, 2nd) — 3rd is anyone else
    third_orderings = [(i, j), (j, i)]  # (1st, 3rd) — 2nd is anyone else
    twoth_orderings = [(i, j), (j, i)]  # (2nd, 3rd) — 1st is anyone else

    # Pattern 1: i,j occupy positions 1 & 2 (any of 2 orderings); 3rd is other
    for a, b in pair_orderings:
        denom1 = S - v[a]
        if denom1 <= 0:
            continue
        for k in range(n):
            if k == a or k == b:
                continue
            denom2 = S - v[a] - v[b]
            if denom2 <= 0:
                continue
            p += (v[a] / S) * (v[b] / denom1) * (v[k] / denom2)

    # Pattern 2: 1st = i or j, 3rd = j or i, 2nd = other
    for a, c in third_orderings:
        denom1 = S - v[a]
        if denom1 <= 0:
            continue
        for k in range(n):
            if k == a or k == c:
                continue
            denom2 = S - v[a] - v[k]
            if denom2 <= 0:
                continue
            p += (v[a] / S) * (v[k] / denom1) * (v[c] / denom2)

    # Pattern 3: 2nd = i or j, 3rd = j or i, 1st = other
    for b, c in twoth_orderings:
        for k in range(n):
            if k == b or k == c:
                continue
            denom1 = S - v[k]
            if denom1 <= 0:
                continue
            denom2 = S - v[k] - v[b]
            if denom2 <= 0:
                continue
            p += (v[k] / S) * (v[b] / denom1) * (v[c] / denom2)

    return float(p)


def prob_unordered_top3(prob_win: list[float], i: int, j: int, k: int) -> float:
    """P({i,j,k} are the top-3 finishers, in any order)."""
    v = _pl_v(prob_win)
    n = len(v)
    if any(x < 0 or x >= n for x in (i, j, k)) or len({i, j, k}) < 3:
        return 0.0
    S = float(v.sum())
    if S <= 0:
        return 0.0
    p = 0.0
    for a, b, c in permutations((i, j, k)):
        denom1 = S - v[a]
        denom2 = denom1 - v[b]
        if denom1 <= 0 or denom2 <= 0:
            continue
        p += (v[a] / S) * (v[b] / denom1) * (v[c] / denom2)
    return float(p)


def prob_ordered_top3(
    prob_win: list[float], i: int, j: int, k: int
) -> float:
    """P(i = 1st, j = 2nd, k = 3rd)."""
    v = _pl_v(prob_win)
    n = len(v)
    if any(x < 0 or x >= n for x in (i, j, k)) or len({i, j, k}) < 3:
        return 0.0
    S = float(v.sum())
    if S <= 0:
        return 0.0
    denom1 = S - v[i]
    denom2 = denom1 - v[j]
    if denom1 <= 0 or denom2 <= 0:
        return 0.0
    return float((v[i] / S) * (v[j] / denom1) * (v[k] / denom2))


# ----- EV tables -----

def _combo_key_pair(a: int, b: int, ordered: bool = False) -> str:
    """JRDB combo key for a pair: '01-02' (sorted if not ordered)."""
    if not ordered and a > b:
        a, b = b, a
    return f"{a:02d}-{b:02d}"


def _combo_key_triplet(a: int, b: int, c: int) -> str:
    """JRDB sorted combo key for a triplet: '01-02-03'."""
    s = sorted((a, b, c))
    return f"{s[0]:02d}-{s[1]:02d}-{s[2]:02d}"


def compute_wide_ev(
    horse_numbers: list[int],
    prob_win: list[float],
    odds: dict[str, float],
) -> list[dict]:
    """EV for every wide combo (i<j). Returns list of dicts sorted by ev desc.

    EV = P(i,j ∈ top3) × wide_odds_{ij}.
    """
    _check_horses(horse_numbers, prob_win)
    out: list[dict] = []
    for ai, hi in enumerate(horse_numbers):
        for aj in range(ai + 1, len(horse_numbers)):
            hj = horse_numbers[aj]
            key = _combo_key_pair(hi, hj)
            o = odds.get(key)
            if o is None or o <= 0:
                continue
            p = prob_pair_in_top3(prob_win, ai, aj)
            ev = p * o
            out.append({
                "combo": (hi, hj), "key": key, "prob": p, "odds": o, "ev": ev,
            })
    out.sort(key=lambda d: d["ev"], reverse=True)
    return out


def compute_umatan_ev(
    horse_numbers: list[int],
    prob_win: list[float],
    odds: dict[str, float],
) -> list[dict]:
    """EV for every umatan ordered pair (i, j with i ≠ j)."""
    _check_horses(horse_numbers, prob_win)
    out: list[dict] = []
    for ai, hi in enumerate(horse_numbers):
        for aj, hj in enumerate(horse_numbers):
            if ai == aj:
                continue
            key = _combo_key_pair(hi, hj, ordered=True)
            o = odds.get(key)
            if o is None or o <= 0:
                continue
            p = prob_pair_top1_2(prob_win, ai, aj)
            ev = p * o
            out.append({
                "combo": (hi, hj), "key": key, "prob": p, "odds": o, "ev": ev,
            })
    out.sort(key=lambda d: d["ev"], reverse=True)
    return out


def compute_sanrenpuku_ev(
    horse_numbers: list[int],
    prob_win: list[float],
    odds: dict[str, float],
) -> list[dict]:
    """EV for every sanrenpuku unordered triplet."""
    _check_horses(horse_numbers, prob_win)
    out: list[dict] = []
    for ai, aj, ak in combinations(range(len(horse_numbers)), 3):
        hi, hj, hk = horse_numbers[ai], horse_numbers[aj], horse_numbers[ak]
        key = _combo_key_triplet(hi, hj, hk)
        o = odds.get(key)
        if o is None or o <= 0:
            continue
        p = prob_unordered_top3(prob_win, ai, aj, ak)
        ev = p * o
        out.append({
            "combo": tuple(sorted((hi, hj, hk))),
            "key": key, "prob": p, "odds": o, "ev": ev,
        })
    out.sort(key=lambda d: d["ev"], reverse=True)
    return out


def compute_tan_ev(
    horse_numbers: list[int],
    prob_win: list[float],
    odds_tan: dict[int, float],
) -> list[dict]:
    """EV for 単勝: P(win_i) × odds_tan_i.

    ``odds_tan`` maps horse_number → win odds.
    """
    _check_horses(horse_numbers, prob_win)
    out: list[dict] = []
    for ai, h in enumerate(horse_numbers):
        o = odds_tan.get(h)
        if o is None or o <= 0:
            continue
        p = prob_win[ai]
        out.append({"horse": h, "prob": p, "odds": o, "ev": p * o})
    out.sort(key=lambda d: d["ev"], reverse=True)
    return out


def compute_fuku_ev(
    horse_numbers: list[int],
    prob_top3: list[float],
    odds_fuku: dict[int, float],
) -> list[dict]:
    """EV for 複勝: P(top3_i) × odds_fuku_i."""
    _check_horses(horse_numbers, prob_top3)
    out: list[dict] = []
    for ai, h in enumerate(horse_numbers):
        o = odds_fuku.get(h)
        if o is None or o <= 0:
            continue
        p = prob_top3[ai]
        out.append({"horse": h, "prob": p, "odds": o, "ev": p * o})
    out.sort(key=lambda d: d["ev"], reverse=True)
    return out


# ----- Recommended bet generation (Phase 4-B) -----

def recommend_threshold(
    ev_table: list[dict],
    threshold: float,
    max_bets: int = 20,
) -> list[dict]:
    """Pick bets with EV > threshold, capped at ``max_bets``.

    ``ev_table`` is the output of any compute_*_ev function (already sorted
    by EV desc).
    """
    return [row for row in ev_table if row["ev"] > threshold][:max_bets]


def recommend_nagashi_axis(
    ev_table: list[dict],
    axis_horse: int,
    threshold: float,
    max_partners: int = 5,
) -> list[dict]:
    """Pick bets where axis_horse is in the combo and EV > threshold.

    Useful for 馬単 1着固定流し or 三連複 軸 1 頭流し. Caller picks ``axis_horse``
    (e.g. highest prob_win) and supplies the relevant ``ev_table``.
    """
    out = []
    for row in ev_table:
        combo = row.get("combo")
        if combo is None or axis_horse not in combo:
            continue
        if row["ev"] <= threshold:
            continue
        out.append(row)
        if len(out) >= max_partners:
            break
    return out
