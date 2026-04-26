"""Backtest read + run endpoints."""
from __future__ import annotations

import time
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.api.deps import DbSession
from src.api.schemas import (
    BacktestRunRequest,
    BacktestRunResponse,
    EquityPoint,
    SensitivityRow,
    Strategy,
)
from src.backtest import (
    STRATEGIES,
    build_equity_curve,
    load_hjc_df,
    load_predictions_df,
    run_backtest,
    run_sensitivity_sweep,
)
from src.backtest.runner import EV_STRATEGIES, latest_model_version
from src.db.models import (
    BacktestDetail,
    BacktestRun,
    BacktestSensitivity,
)

router = APIRouter(prefix="/backtest", tags=["backtest"])


def _kind(strategy: str) -> str:
    return "EV" if strategy in EV_STRATEGIES else "ML"


def _to_strategy_schema(run: BacktestRun) -> Strategy:
    held_lookup: dict[str, "object"] = {}  # not needed — equity uses detail rows
    monthly: dict[str, int] = {}
    for d in sorted(run.details, key=lambda x: x.held_on):
        pnl = (d.return_amount or 0) - (d.bets or 0)
        m = d.held_on.strftime("%Y-%m")
        monthly[m] = monthly.get(m, 0) + pnl
    cum = 0
    points: list[EquityPoint] = []
    for m in sorted(monthly):
        cum += monthly[m]
        points.append(EquityPoint(month=m, cum=cum))

    return Strategy(
        run_id=run.id,
        id=run.strategy,
        label=run.strategy,
        kind=_kind(run.strategy),
        date_from=run.date_from,
        date_to=run.date_to,
        ev_threshold=run.ev_threshold,
        model_version=run.model_version,
        races=run.races or 0,
        bet_races=run.bet_races or 0,
        invested=run.invested or 0,
        returned=run.returned or 0,
        hits=run.hits or 0,
        roi=run.roi or 0.0,
        equity=points,
        computed_at=run.computed_at,
    )


@router.get("/strategies", response_model=list[Strategy])
def list_strategies(
    session: DbSession,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[Strategy]:
    """Latest run per strategy (most recent computed_at wins).

    If both date_from and date_to are given, only runs whose period exactly
    matches are returned. With no date params, the latest run of any period
    is returned (legacy behavior).
    """
    stmt = (
        select(BacktestRun)
        .options(selectinload(BacktestRun.details))
        .order_by(BacktestRun.strategy, BacktestRun.computed_at.desc())
    )
    if date_from is not None and date_to is not None:
        stmt = stmt.where(
            BacktestRun.date_from == date_from,
            BacktestRun.date_to == date_to,
        )
    runs = session.scalars(stmt).all()

    seen: set[str] = set()
    latest: list[BacktestRun] = []
    for r in runs:
        if r.strategy in seen:
            continue
        seen.add(r.strategy)
        latest.append(r)
    return [_to_strategy_schema(r) for r in latest]


@router.get("/{run_id}/sensitivity", response_model=list[SensitivityRow])
def get_sensitivity(run_id: int, session: DbSession) -> list[SensitivityRow]:
    rows = session.scalars(
        select(BacktestSensitivity)
        .where(BacktestSensitivity.run_id == run_id)
        .order_by(BacktestSensitivity.ev_threshold)
    ).all()
    return [
        SensitivityRow(
            thr=r.ev_threshold,
            bet_races=r.bet_races,
            hits=r.hits,
            roi=r.roi,
        )
        for r in rows
    ]


@router.post("/run", response_model=BacktestRunResponse)
def run(req: BacktestRunRequest, session: DbSession) -> BacktestRunResponse:
    started = time.perf_counter()

    targets = STRATEGIES if req.strategy == "all" else [req.strategy]
    for s in targets:
        if s not in STRATEGIES:
            raise HTTPException(400, f"Unknown strategy: {s}")

    mv = latest_model_version(session)
    if mv is None:
        raise HTTPException(409, "No predictions in DB; run predict first")

    preds_df = load_predictions_df(session, req.date_from, req.date_to, mv)
    hjc_df = load_hjc_df(session, req.date_from, req.date_to)
    if preds_df.empty or hjc_df.empty:
        missing = []
        if preds_df.empty:
            missing.append("predictions")
        if hjc_df.empty:
            missing.append("payouts (HJC)")
        raise HTTPException(
            422,
            f"No {' and '.join(missing)} in {req.date_from}..{req.date_to}",
        )

    out: list[Strategy] = []
    for s in targets:
        run_obj = run_backtest(
            session,
            strategy=s,
            date_from=req.date_from,
            date_to=req.date_to,
            ev_threshold=req.ev_threshold,
            model_version=mv,
        )
        if req.sensitivity and s in EV_STRATEGIES:
            run_sensitivity_sweep(session, run=run_obj, preds_df=preds_df, hjc_df=hjc_df)
        session.commit()
        # re-fetch with details for schema serialization
        run_obj = session.scalar(
            select(BacktestRun)
            .where(BacktestRun.id == run_obj.id)
            .options(selectinload(BacktestRun.details))
        )
        out.append(_to_strategy_schema(run_obj))

    return BacktestRunResponse(runs=out, elapsed_ms=int((time.perf_counter() - started) * 1000))
