"""Batch backtest runner: predict once, evaluate many strategies.

The default `python cli.py evaluate` makes one Modal predict call per race
synchronously, which is impractically slow over a full year (~3000 races
× per-RPC overhead ≈ hours per strategy). This script collapses that into
a small number of batched Modal calls, then runs every strategy locally
against the cached predictions.

Usage:
    source .venv/bin/activate
    python scripts/run_backtest.py --date-range 20250101 20251228
    python scripts/run_backtest.py --date-range 20250101 20251228 \
        --predictions-cache out/backtest_20260425/preds_2025.parquet
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from config.settings import Settings  # noqa: E402
from src.features.engineering import build_prediction_features  # noqa: E402
from src.model.client import ModalClient  # noqa: E402
from src.parser import (  # noqa: E402
    HJC_FIELDS,
    HJC_RECORD_LENGTH,
    KYI_FIELDS,
    KYI_RECORD_LENGTH,
)
from src.parser.engine import build_race_key, parse_file  # noqa: E402
from src.predict.roi import evaluate_roi  # noqa: E402

EV_STRATEGIES = ["ev_tansho", "ev_fukusho", "ev_sanrenpuku_nagashi"]
BASELINE_STRATEGIES = ["fukusho_top3", "umaren_top2", "sanrenpuku_top3"]


def _filter_by_date_range(paths: list[Path], date_range: tuple[str, str]) -> list[Path]:
    """Filter file paths by YYYYMMDD date range. Filenames use YYMMDD."""
    start = datetime.strptime(date_range[0], "%Y%m%d")
    end = datetime.strptime(date_range[1], "%Y%m%d")
    out = []
    for p in paths:
        date_part = p.stem[3:]
        if len(date_part) != 6 or not date_part.isdigit():
            continue
        try:
            d = datetime.strptime(date_part, "%y%m%d")
        except ValueError:
            continue
        if start <= d <= end:
            out.append(p)
    return out


def _load_kyi(settings: Settings, date_range: tuple[str, str]) -> pd.DataFrame:
    paths = _filter_by_date_range(
        sorted(settings.data_raw_dir.glob("KYI*.txt")), date_range,
    )
    if not paths:
        raise SystemExit(f"No KYI files in {date_range}")
    print(f"Loading {len(paths)} KYI files...")
    return pd.concat(
        [parse_file(p, KYI_FIELDS, KYI_RECORD_LENGTH) for p in paths],
        ignore_index=True,
    )


def _load_hjc(settings: Settings, date_range: tuple[str, str]) -> pd.DataFrame:
    paths = _filter_by_date_range(
        sorted(settings.data_raw_dir.glob("HJC*.txt")), date_range,
    )
    if not paths:
        raise SystemExit(f"No HJC files in {date_range}")
    print(f"Loading {len(paths)} HJC files...")
    frames = []
    for p in paths:
        df = parse_file(p, HJC_FIELDS, HJC_RECORD_LENGTH)
        df["race_key"] = df.apply(lambda r: build_race_key(r.to_dict()), axis=1)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _predict_batched(
    client: ModalClient,
    features_df: pd.DataFrame,
    batch_rows: int,
) -> list[float]:
    """Predict in race-aligned chunks no larger than batch_rows."""
    feature_cols = [
        c for c in features_df.columns
        if c not in ("race_key", "horse_name", "fukusho_odds")
    ]

    chunks: list[list[dict]] = []
    current: list[dict] = []
    cur_indices: list[int] = []
    chunk_indices: list[list[int]] = []
    for race_key, race_df in features_df.groupby("race_key", sort=False):
        race_records = race_df[feature_cols].to_dict("records")
        race_idx = race_df.index.tolist()
        if current and len(current) + len(race_records) > batch_rows:
            chunks.append(current)
            chunk_indices.append(cur_indices)
            current = []
            cur_indices = []
        current.extend(race_records)
        cur_indices.extend(race_idx)
    if current:
        chunks.append(current)
        chunk_indices.append(cur_indices)

    print(f"Sending {len(chunks)} batched Modal predict calls"
          f" ({sum(len(c) for c in chunks)} total rows)...")

    preds_by_idx: dict[int, float] = {}
    for i, (chunk, idx_list) in enumerate(zip(chunks, chunk_indices), start=1):
        result = client.predict(chunk)
        if not result.get("success"):
            raise SystemExit(f"Batch {i} failed: {result}")
        for idx, prob in zip(idx_list, result["predictions"]):
            preds_by_idx[idx] = prob
        print(f"  batch {i}/{len(chunks)} done ({len(chunk)} rows)")

    return [preds_by_idx[i] for i in features_df.index]


def _build_predictions_df(features_df: pd.DataFrame, preds: list[float]) -> pd.DataFrame:
    df = features_df.copy()
    df["predict_prob"] = preds
    keep = ["race_key", "horse_number", "predict_prob"]
    if "odds" in df.columns:
        keep.append("odds")
    if "fukusho_odds" in df.columns:
        keep.append("fukusho_odds")
    return df[keep].reset_index(drop=True)


def _format_result(name: str, result: dict) -> str:
    bet_races = result.get("bet_race_count")
    bet_str = f", 購入{bet_races}R" if bet_races is not None else ""
    return (
        f"{name:>32s} | レース {result['race_count']:4d}{bet_str}"
        f" | 投資 {result['total_bets']:>10,}円"
        f" | 回収 {result['total_return']:>10,}円"
        f" | ROI {result['roi']:>6.1f}%"
        f" | 的中 {result['hit_count']:4d}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-range", nargs=2, required=True,
                        metavar=("START", "END"), help="YYYYMMDD YYYYMMDD")
    parser.add_argument("--batch-rows", type=int, default=2000,
                        help="Max rows per Modal predict call (default: 2000)")
    parser.add_argument("--predictions-cache", type=Path, default=None,
                        help="Path to .csv cache. Loaded if exists, saved otherwise.")
    parser.add_argument("--ev-thresholds", nargs="+", type=float,
                        default=[0.9, 1.0, 1.1, 1.2],
                        help="EV thresholds to sweep")
    parser.add_argument("--out", type=Path, default=Path("out/backtest_20260425"),
                        help="Output directory for the result table")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    settings = Settings()

    if args.predictions_cache and args.predictions_cache.exists():
        print(f"Loading cached predictions from {args.predictions_cache}")
        predictions_df = pd.read_csv(args.predictions_cache)
    else:
        kyi_df = _load_kyi(settings, tuple(args.date_range))
        print("Building prediction features...")
        features_df = build_prediction_features(kyi_df).reset_index(drop=True)
        print(f"Got {len(features_df)} rows over"
              f" {features_df['race_key'].nunique()} races.")

        client = ModalClient()
        preds = _predict_batched(client, features_df, args.batch_rows)
        predictions_df = _build_predictions_df(features_df, preds)
        if args.predictions_cache:
            predictions_df.to_csv(args.predictions_cache, index=False)
            print(f"Saved predictions cache to {args.predictions_cache}")

    hjc_df = _load_hjc(settings, tuple(args.date_range))

    print("\n=== Backtest results ===")
    rows: list[str] = []

    for strat in BASELINE_STRATEGIES:
        result = evaluate_roi(predictions_df, hjc_df, strategy=strat)
        line = _format_result(strat, result)
        print(line)
        rows.append(line)

    for strat in EV_STRATEGIES:
        for thr in args.ev_thresholds:
            result = evaluate_roi(predictions_df, hjc_df, strategy=strat, ev_threshold=thr)
            label = f"{strat} (EV>{thr:.2f})"
            line = _format_result(label, result)
            print(line)
            rows.append(line)

    out_path = args.out / f"results_{args.date_range[0]}_{args.date_range[1]}.txt"
    out_path.write_text("\n".join(rows) + "\n")
    print(f"\nSaved results to {out_path}")


if __name__ == "__main__":
    main()
