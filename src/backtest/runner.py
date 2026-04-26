"""Run backtest strategies against DB-stored predictions and payouts.

Pipeline: DB rows → DataFrame → evaluate_roi (existing logic) → BacktestRun
+ BacktestDetail + BacktestSensitivity rows.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.db.models import (
    BacktestDetail,
    BacktestRun,
    BacktestSensitivity,
    HjcPayout,
    HorseEntry,
    Prediction,
    Race,
    RaceOdds,
)
from src.predict.roi import evaluate_roi

STRATEGIES: list[str] = [
    "fukusho_top3",
    "umaren_top2",
    "sanrenpuku_top3",
    "ev_tansho",
    "ev_fukusho",
    "ev_sanrenpuku_nagashi",
    # Phase 4 — multibet EV (Plackett-Luce + pre-race combination odds)
    "ev_wide",
    "ev_umatan",
    "ev_sanrenpuku_box",
]

EV_STRATEGIES: set[str] = {
    "ev_tansho",
    "ev_fukusho",
    "ev_sanrenpuku_nagashi",
    "ev_wide",
    "ev_umatan",
    "ev_sanrenpuku_box",
}

# Strategies that require pre-race combination odds (race_odds_df)
MULTIBET_STRATEGIES: set[str] = {"ev_wide", "ev_umatan", "ev_sanrenpuku_box"}

# Sensitivity sweep: 0.80 → 1.50 step 0.05 (matches TweaksPanel slider).
SENSITIVITY_THRESHOLDS: list[float] = [round(0.80 + 0.05 * i, 2) for i in range(15)]


# ─────────── DB → DataFrame ───────────


def load_predictions_df(
    session: Session,
    date_from: date,
    date_to: date,
    model_version: Optional[str] = None,
) -> pd.DataFrame:
    """Predictions joined with horse_entry + race → flat DataFrame.

    Columns: race_key, horse_number, predict_prob, odds, fukusho_odds, held_on.
    """
    stmt = (
        select(
            Race.race_key,
            Race.held_on,
            HorseEntry.horse_number,
            HorseEntry.odds,
            HorseEntry.fukusho_odds,
            Prediction.prob,
            Prediction.prob_win,
            Prediction.model_version,
        )
        .join(HorseEntry, HorseEntry.race_id == Race.id)
        .join(Prediction, Prediction.horse_entry_id == HorseEntry.id)
        .where(Race.held_on.between(date_from, date_to))
    )
    if model_version is not None:
        stmt = stmt.where(Prediction.model_version == model_version)

    rows = session.execute(stmt).all()
    if not rows:
        return pd.DataFrame(
            columns=[
                "race_key", "horse_number", "predict_prob", "prob_win",
                "odds", "fukusho_odds", "held_on",
            ]
        )
    df = pd.DataFrame(rows, columns=[
        "race_key", "held_on", "horse_number", "odds", "fukusho_odds",
        "predict_prob", "prob_win", "model_version",
    ])
    return df


def load_race_odds_df(
    session: Session,
    date_from: date,
    date_to: date,
) -> pd.DataFrame:
    """Pre-race combination odds (OW/OU/OT) for races in the date range."""
    rows = session.execute(
        select(
            Race.race_key,
            RaceOdds.head_count,
            RaceOdds.wide,
            RaceOdds.umatan,
            RaceOdds.sanrenpuku,
        )
        .join(RaceOdds, RaceOdds.race_id == Race.id)
        .where(Race.held_on.between(date_from, date_to))
    ).all()
    if not rows:
        return pd.DataFrame(
            columns=["race_key", "head_count", "wide", "umatan", "sanrenpuku"]
        )
    return pd.DataFrame(rows, columns=[
        "race_key", "head_count", "wide", "umatan", "sanrenpuku",
    ])


def load_hjc_df(session: Session, date_from: date, date_to: date) -> pd.DataFrame:
    """hjc_payout.raw JSON expanded back to a wide DataFrame for evaluate_roi."""
    rows = session.execute(
        select(Race.race_key, HjcPayout.raw)
        .join(HjcPayout, HjcPayout.race_id == Race.id)
        .where(Race.held_on.between(date_from, date_to))
    ).all()
    if not rows:
        return pd.DataFrame()
    records = []
    for race_key, raw in rows:
        d = dict(raw or {})
        d["race_key"] = race_key
        records.append(d)
    return pd.DataFrame(records)


def latest_model_version(session: Session) -> Optional[str]:
    return session.scalar(
        select(Prediction.model_version)
        .order_by(Prediction.predicted_at.desc())
        .limit(1)
    )


# ─────────── Equity curve ───────────


def build_equity_curve(
    details: list[dict],
    held_on_lookup: dict[str, date],
) -> list[dict]:
    """Aggregate per-race PnL into monthly cumulative points.

    Args:
        details: evaluate_roi's `details` list — each dict has race_key, bets, return.
        held_on_lookup: race_key → date.

    Returns:
        list[{month: 'YYYY-MM', cum: int}] sorted by month.
    """
    monthly: dict[str, int] = {}
    for d in details:
        race_key = d.get("race_key")
        held = held_on_lookup.get(race_key)
        if held is None:
            continue
        bets = int(d.get("bets") or 0)
        ret = int(d.get("return") or 0)
        pnl = ret - bets
        month = held.strftime("%Y-%m")
        monthly[month] = monthly.get(month, 0) + pnl

    cum = 0
    points: list[dict] = []
    for month in sorted(monthly):
        cum += monthly[month]
        points.append({"month": month, "cum": cum})
    return points


# ─────────── Backtest run + persist ───────────


def _persist_run(
    session: Session,
    *,
    strategy: str,
    date_from: date,
    date_to: date,
    ev_threshold: Optional[float],
    model_version: str,
    result: dict,
    held_on_lookup: dict[str, date],
) -> BacktestRun:
    """Replace any existing run with same key, then write new run + details."""
    existing = session.scalar(
        select(BacktestRun).where(
            BacktestRun.strategy == strategy,
            BacktestRun.date_from == date_from,
            BacktestRun.date_to == date_to,
            BacktestRun.ev_threshold == ev_threshold,
            BacktestRun.model_version == model_version,
        )
    )
    if existing is not None:
        session.delete(existing)
        session.flush()

    run = BacktestRun(
        strategy=strategy,
        date_from=date_from,
        date_to=date_to,
        ev_threshold=ev_threshold,
        model_version=model_version,
        races=result.get("race_count"),
        bet_races=result.get("bet_race_count") or result.get("race_count"),
        invested=result.get("total_bets"),
        returned=result.get("total_return"),
        hits=result.get("hit_count"),
        roi=result.get("roi"),
        computed_at=datetime.utcnow(),
    )
    session.add(run)
    session.flush()

    # Resolve race_key → race.id once
    race_id_map = dict(session.execute(
        select(Race.race_key, Race.id).where(Race.race_key.in_(held_on_lookup.keys()))
    ).all())

    for d in result.get("details", []):
        race_key = d.get("race_key")
        race_id = race_id_map.get(race_key)
        held = held_on_lookup.get(race_key)
        if race_id is None or held is None:
            continue
        session.add(BacktestDetail(
            run_id=run.id,
            race_id=race_id,
            held_on=held,
            bets=int(d.get("bets") or 0),
            return_amount=int(d.get("return") or 0),
            hit=1 if d.get("hit") else 0,
        ))
    return run


def run_backtest(
    session: Session,
    *,
    strategy: str,
    date_from: date,
    date_to: date,
    ev_threshold: Optional[float] = None,
    model_version: Optional[str] = None,
) -> BacktestRun:
    """Run one strategy and persist results to DB."""
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")

    mv = model_version or latest_model_version(session)
    if mv is None:
        raise ValueError("No predictions in DB; run predict first")

    preds_df = load_predictions_df(session, date_from, date_to, mv)
    hjc_df = load_hjc_df(session, date_from, date_to)
    if preds_df.empty or hjc_df.empty:
        raise ValueError("No predictions or payouts in date range")

    held_on_lookup = (
        preds_df[["race_key", "held_on"]]
        .drop_duplicates()
        .set_index("race_key")["held_on"]
        .to_dict()
    )

    thr = ev_threshold if strategy in EV_STRATEGIES else None
    race_odds_df = None
    if strategy in MULTIBET_STRATEGIES:
        race_odds_df = load_race_odds_df(session, date_from, date_to)
        if race_odds_df.empty:
            raise ValueError(
                f"Strategy {strategy} requires race_odds; ingest OW/OU/OT first"
            )
    result = evaluate_roi(
        preds_df,
        hjc_df,
        strategy=strategy,
        ev_threshold=thr if thr is not None else 1.0,
        race_odds_df=race_odds_df,
    )

    return _persist_run(
        session,
        strategy=strategy,
        date_from=date_from,
        date_to=date_to,
        ev_threshold=thr,
        model_version=mv,
        result=result,
        held_on_lookup=held_on_lookup,
    )


def run_sensitivity_sweep(
    session: Session,
    *,
    run: BacktestRun,
    preds_df: pd.DataFrame,
    hjc_df: pd.DataFrame,
    thresholds: list[float] = SENSITIVITY_THRESHOLDS,
) -> int:
    """Sweep ev_threshold for the run's strategy, store under backtest_sensitivity."""
    if run.strategy not in EV_STRATEGIES:
        return 0

    # Replace prior sensitivity rows for this run
    session.execute(delete(BacktestSensitivity).where(BacktestSensitivity.run_id == run.id))
    session.flush()

    race_odds_df = None
    if run.strategy in MULTIBET_STRATEGIES:
        race_odds_df = load_race_odds_df(session, run.date_from, run.date_to)

    written = 0
    for thr in thresholds:
        res = evaluate_roi(
            preds_df,
            hjc_df,
            strategy=run.strategy,
            ev_threshold=thr,
            race_odds_df=race_odds_df,
        )
        session.add(BacktestSensitivity(
            run_id=run.id,
            ev_threshold=thr,
            bet_races=res.get("bet_race_count"),
            hits=res.get("hit_count"),
            roi=res.get("roi"),
        ))
        written += 1
    return written
