"""MODEL tab — training runs, leaderboard, feature importance, calibration."""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, text

from src.api.deps import DbSession
from src.api.schemas import (
    CalibrationBin,
    CalibrationResponse,
    FeatureImportanceRow,
    LeaderboardResponse,
    LeaderboardRow,
    ModelStatusOut,
    TrainingRunOut,
)
from src.db.models import TrainingRun
from src.features.columns import FIELD_TO_FEATURE

router = APIRouter(prefix="/model", tags=["model"])


def _reverse_label_lookup() -> dict[str, str]:
    return {ml: jp for jp, ml in FIELD_TO_FEATURE.items()}


def _get_deployed(session) -> Optional[TrainingRun]:
    return session.scalar(
        select(TrainingRun)
        .where(TrainingRun.status == "DEPLOYED")
        .order_by(TrainingRun.trained_at.desc())
        .limit(1)
    )


def _get_run(session, run_id: Optional[str]) -> Optional[TrainingRun]:
    if run_id:
        return session.scalar(select(TrainingRun).where(TrainingRun.run_id == run_id))
    return _get_deployed(session)


@router.get("/status", response_model=ModelStatusOut)
def get_status(session: DbSession) -> ModelStatusOut:
    deployed = _get_deployed(session)

    modal_ready = False
    modal_info: dict = {}
    try:
        from src.model.client import ModalClient

        info = ModalClient().get_model_status()
        if isinstance(info, dict) and info.get("exists"):
            modal_ready = True
            modal_info = info
    except Exception:
        modal_ready = False

    if deployed:
        return ModelStatusOut(
            deployed_run_id=deployed.run_id,
            trained_at=deployed.trained_at,
            num_samples=deployed.num_samples,
            best_score=deployed.auc,
            preset=deployed.preset,
            modal_ready=modal_ready,
        )

    trained_at_raw = modal_info.get("trained_at")
    trained_at: Optional[datetime] = None
    if trained_at_raw:
        try:
            trained_at = datetime.fromisoformat(str(trained_at_raw).replace("Z", "+00:00"))
        except ValueError:
            trained_at = None

    return ModelStatusOut(
        deployed_run_id=None,
        trained_at=trained_at,
        num_samples=modal_info.get("num_samples"),
        best_score=modal_info.get("best_score"),
        preset=None,
        modal_ready=modal_ready,
    )


@router.get("/training-runs", response_model=list[TrainingRunOut])
def get_training_runs(session: DbSession, limit: int = 6) -> list[TrainingRunOut]:
    rows = session.scalars(
        select(TrainingRun).order_by(TrainingRun.trained_at.desc()).limit(limit)
    ).all()
    return [
        TrainingRunOut(
            id=r.id,
            run_id=r.run_id,
            trained_at=r.trained_at,
            preset=r.preset,
            logloss=r.logloss,
            auc=r.auc,
            brier=r.brier,
            hit_at_3=r.hit_at_3,
            train_time_seconds=r.train_time_seconds,
            num_samples=r.num_samples,
            status=r.status,
        )
        for r in rows
    ]


@router.get("/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(
    session: DbSession, run_id: Optional[str] = None
) -> LeaderboardResponse:
    run = _get_run(session, run_id)
    if not run or not run.leaderboard_json:
        return LeaderboardResponse(run_id=run.run_id if run else None, rows=[])
    try:
        records = json.loads(run.leaderboard_json)
    except json.JSONDecodeError:
        return LeaderboardResponse(run_id=run.run_id, rows=[])

    rows: list[LeaderboardRow] = []
    for rec in records:
        rows.append(
            LeaderboardRow(
                model=str(
                    rec.get("model")
                    or rec.get("model_name")
                    or rec.get("name")
                    or "?"
                ),
                score_val=_as_float(
                    rec.get("score_val")
                    or rec.get("score_test")
                    or rec.get("score")
                ),
                eval_metric=_as_str(rec.get("eval_metric") or rec.get("metric")),
                fit_time=_as_float(rec.get("fit_time") or rec.get("fit_time_marginal")),
                weight=_as_float(rec.get("weight") or rec.get("ensemble_weight")),
            )
        )
    return LeaderboardResponse(run_id=run.run_id, rows=rows)


def _as_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_str(v) -> Optional[str]:
    if v is None:
        return None
    return str(v)


_FEATURE_IMPORTANCE_CACHE: dict[str, tuple[float, list[FeatureImportanceRow]]] = {}
_IMPORTANCE_TTL = 600.0


@router.get("/feature-importance", response_model=list[FeatureImportanceRow])
def get_feature_importance() -> list[FeatureImportanceRow]:
    cached = _FEATURE_IMPORTANCE_CACHE.get("default")
    if cached and (time.time() - cached[0]) < _IMPORTANCE_TTL:
        return cached[1]

    try:
        from src.model.client import ModalClient

        result = ModalClient().get_feature_importance()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Modal call failed: {e}") from e

    if not isinstance(result, dict) or not result.get("success"):
        return []

    features = result.get("features") or result.get("importance") or []
    rev = _reverse_label_lookup()
    rows: list[FeatureImportanceRow] = []
    for entry in features:
        if isinstance(entry, dict):
            name = str(entry.get("name") or entry.get("feature") or "?")
            imp = entry.get("importance")
        else:
            name, imp = "?", None
        rows.append(
            FeatureImportanceRow(
                name=name,
                jp_label=rev.get(name),
                importance=float(imp) if imp is not None else 0.0,
            )
        )
    rows.sort(key=lambda r: r.importance, reverse=True)
    _FEATURE_IMPORTANCE_CACHE["default"] = (time.time(), rows)
    return rows


_CALIBRATION_CACHE: dict[str, tuple[float, CalibrationResponse]] = {}
_CALIBRATION_TTL = 600.0


@router.get("/calibration", response_model=CalibrationResponse)
def get_calibration(
    session: DbSession, run_id: Optional[str] = None
) -> CalibrationResponse:
    run = _get_run(session, run_id)
    cache_key = run.run_id if run else "_none"
    cached = _CALIBRATION_CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _CALIBRATION_TTL:
        return cached[1]

    if not run:
        empty = CalibrationResponse(run_id=None, bins=[], n_total=0)
        return empty

    window_from = run.trained_at.date()
    rows = session.execute(
        text(
            """
            SELECT p.prob AS prob,
                   CASE WHEN h.goal_position IS NOT NULL AND h.goal_position <= 3
                        THEN 1 ELSE 0 END AS is_place
              FROM prediction p
              JOIN horse_entry h ON h.id = p.horse_entry_id
              JOIN race r ON r.id = h.race_id
             WHERE r.held_on >= :window_from
               AND h.goal_position IS NOT NULL
            """
        ),
        {"window_from": window_from},
    ).all()

    bins_acc = [{"sum_pred": 0.0, "sum_actual": 0, "n": 0} for _ in range(10)]
    n_total = 0
    window_to: Optional[datetime] = None
    for prob, is_place in rows:
        idx = min(9, max(0, int(float(prob) * 10)))
        bins_acc[idx]["sum_pred"] += float(prob)
        bins_acc[idx]["sum_actual"] += int(is_place)
        bins_acc[idx]["n"] += 1
        n_total += 1

    bins: list[CalibrationBin] = []
    ece_num = 0.0
    mce = 0.0
    for b in bins_acc:
        n = int(b["n"])
        if n == 0:
            continue
        pred_mid = b["sum_pred"] / n
        actual_rate = b["sum_actual"] / n
        bins.append(CalibrationBin(pred_mid=pred_mid, actual_rate=actual_rate, n=n))
        gap = abs(actual_rate - pred_mid)
        ece_num += gap * (n / n_total)
        mce = max(mce, gap)

    window_to_d = session.execute(
        text("SELECT MAX(r.held_on) FROM race r WHERE r.held_on >= :wf"),
        {"wf": window_from},
    ).scalar()

    response = CalibrationResponse(
        run_id=run.run_id,
        bins=bins,
        ece=ece_num if n_total else None,
        mce=mce if n_total else None,
        n_total=n_total,
        window_from=window_from,
        window_to=window_to_d,
    )
    _CALIBRATION_CACHE[cache_key] = (time.time(), response)
    return response
