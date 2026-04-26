"""Probability calibration metrics and helpers.

Used by Phase 1-D (Brier / Hit@k / ECE on AutoGluon validation set) and
Phase 2 (softmax-with-temperature for LightGBM lambdarank scores → P(win)).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_brier_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Brier score = mean((y_true - y_pred)^2). Lower is better."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean((y_true - y_pred) ** 2))


def compute_ece(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error (ECE) with equal-width bins.

    For each bin of ``y_pred`` values, weighted by bin frequency, accumulate
    ``|mean(y_true) - mean(y_pred)|``. Range: [0, 1]. Lower is better.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    indices = np.digitize(y_pred, bins[1:-1])

    n = len(y_true)
    if n == 0:
        return 0.0

    ece = 0.0
    for b in range(n_bins):
        mask = indices == b
        if not mask.any():
            continue
        weight = mask.sum() / n
        bin_pred = y_pred[mask].mean()
        bin_true = y_true[mask].mean()
        ece += weight * abs(bin_true - bin_pred)
    return float(ece)


def compute_hit_at_k(
    races: pd.DataFrame,
    k: int = 3,
    pred_col: str = "predict_prob",
    label_col: str = "is_place",
    race_col: str = "race_key",
) -> float:
    """Hit@k: fraction of races where at least one of the top-k predicted
    horses has ``label_col == 1``.

    For ``k=3`` on ``is_place``, "hit" = at least 1 of the top-3 predicted
    horses actually finished in top-3.
    """
    if races.empty:
        return 0.0

    hits = 0
    n_races = 0
    for _, group in races.groupby(race_col):
        n_races += 1
        top = group.nlargest(k, pred_col)
        if (top[label_col] == 1).any():
            hits += 1
    return hits / n_races if n_races else 0.0


def softmax_with_temperature(scores: np.ndarray, temperature: float) -> np.ndarray:
    """Softmax with temperature ``T``. ``T → 0`` sharpens, ``T → ∞`` flattens.

    Used by Phase 2 to convert LightGBM lambdarank raw scores into per-race
    P(win) probabilities. Each row of ``scores`` should be one race.
    """
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    s = np.asarray(scores, dtype=float) / temperature
    s = s - s.max(axis=-1, keepdims=True)
    exp = np.exp(s)
    return exp / exp.sum(axis=-1, keepdims=True)


def fit_temperature(
    scores_per_race: list[np.ndarray],
    winner_idx_per_race: list[int],
    grid: tuple[float, ...] = (0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0),
) -> tuple[float, float]:
    """Grid-search the softmax temperature minimizing race-level NLL on winners.

    Args:
        scores_per_race: list of 1D arrays — scores for horses in each race.
        winner_idx_per_race: list of int — index of the actual winner per race.
        grid: temperatures to evaluate.

    Returns:
        ``(best_T, best_nll)``.
    """
    best_T = grid[0]
    best_nll = float("inf")
    for T in grid:
        nll = 0.0
        n = 0
        for scores, winner in zip(scores_per_race, winner_idx_per_race):
            probs = softmax_with_temperature(scores, T)
            p = max(probs[winner], 1e-12)
            nll -= float(np.log(p))
            n += 1
        if n == 0:
            continue
        nll /= n
        if nll < best_nll:
            best_nll = nll
            best_T = float(T)
    return best_T, best_nll
