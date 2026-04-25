"""Calibration check: predict probability vs. actual top-3 hit rate.

Bins predicted ``is_place`` probability in 10% intervals over the holdout
set, and reports the actual top-3 rate per bin. Use this to detect
optimistic / pessimistic skew in the model — relevant because EV-based
betting multiplies these probabilities by odds, so any bias propagates
directly into expected value calculations.

Reuses the predictions cache produced by ``scripts/run_backtest.py`` to
skip Modal calls. Falls back to running Modal predict if no cache.

Usage:
    source .venv/bin/activate
    python scripts/calibration_check.py \
        --year 25 \
        --predictions-cache out/backtest_20260425/preds_2025.csv \
        --out out/backtest_20260425
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from config.settings import Settings  # noqa: E402
from src.features.engineering import build_prediction_features  # noqa: E402
from src.model.client import ModalClient  # noqa: E402
from src.parser import (  # noqa: E402
    KYI_FIELDS,
    KYI_RECORD_LENGTH,
    SED_FIELDS,
    SED_RECORD_LENGTH,
)
from src.parser.engine import build_race_key, parse_file  # noqa: E402


def _load_kyi(settings: Settings, yy: str) -> pd.DataFrame:
    paths = sorted(settings.data_raw_dir.glob(f"KYI{yy}*.txt"))
    if not paths:
        raise SystemExit(f"No KYI files for year {yy}")
    print(f"Loading {len(paths)} KYI files...")
    return pd.concat(
        [parse_file(p, KYI_FIELDS, KYI_RECORD_LENGTH) for p in paths],
        ignore_index=True,
    )


def _load_sed_labels(settings: Settings, yy: str) -> pd.DataFrame:
    """Parse SED for the year and return (race_key, horse_number, is_place)."""
    paths = sorted(settings.data_raw_dir.glob(f"SED{yy}*.txt"))
    if not paths:
        raise SystemExit(f"No SED files for year {yy}")
    print(f"Loading {len(paths)} SED files...")
    sed = pd.concat(
        [parse_file(p, SED_FIELDS, SED_RECORD_LENGTH) for p in paths],
        ignore_index=True,
    )
    sed["race_key"] = sed.apply(lambda r: build_race_key(r.to_dict()), axis=1)
    sed["horse_number"] = pd.to_numeric(sed["馬番"], errors="coerce").astype("Int64")

    # Filter anomalies (取消, 失格 etc.). 異常区分: 0=normal or NaN
    if "異常区分" in sed.columns:
        keep = sed["異常区分"].isna() | (
            pd.to_numeric(sed["異常区分"], errors="coerce") == 0
        )
        sed = sed[keep]

    sed["finish"] = pd.to_numeric(sed["着順"], errors="coerce")
    sed = sed.dropna(subset=["finish", "horse_number"])
    sed["is_place"] = (sed["finish"] <= 3).astype(int)
    return sed[["race_key", "horse_number", "is_place"]]


def _predict_via_modal(client: ModalClient, features_df: pd.DataFrame,
                      batch_rows: int = 2000) -> list[float]:
    feature_cols = [
        c for c in features_df.columns
        if c not in ("race_key", "horse_name", "fukusho_odds")
    ]
    rows = features_df[feature_cols].to_dict("records")
    n = len(rows)
    print(f"Running Modal predict on {n} rows ({(n + batch_rows - 1) // batch_rows} batches)...")
    out: list[float] = []
    for i in range(0, n, batch_rows):
        chunk = rows[i:i + batch_rows]
        result = client.predict(chunk)
        if not result.get("success"):
            raise SystemExit(f"Predict failed: {result}")
        out.extend(result["predictions"])
        print(f"  {min(i + batch_rows, n)}/{n}")
    return out


def _binned_calibration(merged: pd.DataFrame) -> pd.DataFrame:
    bins = [i / 10.0 for i in range(0, 11)]
    cuts = pd.cut(merged["predict_prob"], bins=bins, include_lowest=True)
    grouped = merged.assign(bin=cuts).groupby("bin", observed=True)
    agg = grouped.agg(
        n=("is_place", "size"),
        predicted_mean=("predict_prob", "mean"),
        actual_rate=("is_place", "mean"),
    ).reset_index()
    agg["gap"] = agg["predicted_mean"] - agg["actual_rate"]
    return agg


def _try_plot(agg: pd.DataFrame, out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", label="ideal")
    ax.scatter(agg["predicted_mean"], agg["actual_rate"],
               s=agg["n"].clip(upper=2000) / 10, alpha=0.7, label="bins")
    ax.set_xlabel("Predicted is_place probability (mean per bin)")
    ax.set_ylabel("Actual top-3 rate (per bin)")
    ax.set_title("Calibration plot — predicted vs. actual")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(True, alpha=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    print(f"Saved plot to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", default="25",
                        help="2-digit year of KYI/SED files (e.g. 25)")
    parser.add_argument("--predictions-cache", type=Path, default=None,
                        help="Use cached predictions CSV from run_backtest.py if available")
    parser.add_argument("--out", type=Path, default=Path("out/calibration"))
    args = parser.parse_args()

    settings = Settings()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.predictions_cache and args.predictions_cache.exists():
        print(f"Loading predictions from {args.predictions_cache}")
        preds_df = pd.read_csv(args.predictions_cache)
    else:
        kyi_df = _load_kyi(settings, args.year)
        print("Building prediction features...")
        features_df = build_prediction_features(kyi_df).reset_index(drop=True)
        client = ModalClient()
        preds = _predict_via_modal(client, features_df)
        preds_df = features_df[["race_key", "horse_number"]].copy()
        preds_df["predict_prob"] = preds

    preds_df["horse_number"] = pd.to_numeric(
        preds_df["horse_number"], errors="coerce").astype("Int64")

    labels_df = _load_sed_labels(settings, args.year)

    merged = preds_df.merge(labels_df, on=["race_key", "horse_number"], how="inner")
    print(f"Joined {len(merged)} rows (preds={len(preds_df)} × labels={len(labels_df)})")

    agg = _binned_calibration(merged)
    print("\n=== Calibration table ===")
    print(agg.to_string(index=False))

    table_path = args.out / f"calibration_{args.year}.csv"
    agg.to_csv(table_path, index=False)
    print(f"\nSaved table to {table_path}")

    summary_path = args.out / f"calibration_{args.year}_summary.txt"
    overall_pred = merged["predict_prob"].mean()
    overall_actual = merged["is_place"].mean()
    summary_path.write_text(
        f"Year: {args.year}\n"
        f"N: {len(merged)}\n"
        f"Overall predicted mean: {overall_pred:.4f}\n"
        f"Overall actual rate:    {overall_actual:.4f}\n"
        f"Overall gap (pred - act): {overall_pred - overall_actual:+.4f}\n"
    )
    print(f"Saved summary to {summary_path}")

    _try_plot(agg, args.out / f"calibration_{args.year}.png")


if __name__ == "__main__":
    main()
