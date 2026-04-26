"""Prediction endpoints — calls Modal sync, upserts predictions, returns Horse[]."""
from __future__ import annotations

import time
from datetime import date, datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.api.deps import DbSession
from src.api.routers.races import _horse_to_schema
from src.api.schemas import (
    PredictBatchItem,
    PredictBatchResponse,
    PredictResponse,
)
from src.db.models import HorseEntry, Prediction, Race
from src.features.engineering import build_prediction_features
from src.parser import KYI_FIELDS, KYI_RECORD_LENGTH
from src.parser.engine import parse_file

router = APIRouter(prefix="/races", tags=["predict"])


class PredictBatchRequest(BaseModel):
    date: date


def _resolve_model_version() -> str:
    """Best-effort model_version label. Falls back to 'latest'."""
    try:
        from src.model.client import ModalClient

        info = ModalClient().get_model_status()
        if isinstance(info, dict) and info.get("exists"):
            trained = info.get("trained_at")
            if trained:
                return f"jrdb_predictor@{str(trained)[:10]}"
    except Exception:
        pass
    return "jrdb_predictor@latest"


def _kyi_path_for(held_on: date) -> "tuple[Optional[object], str]":
    """Locate the raw KYI file for a given held_on date."""
    from config.settings import Settings

    settings = Settings()
    yymmdd = held_on.strftime("%y%m%d")
    path = settings.data_raw_dir / f"KYI{yymmdd}.txt"
    if not path.exists():
        return None, f"KYI{yymmdd}.txt not found"
    return path, ""


def _predict_one(session: Session, race: Race, model_version: str) -> tuple[int, str]:
    """Run prediction for one race; upsert prediction rows. Returns (count, error).

    Phase 2 extension: also call the lambdarank model (if deployed) to populate
    ``prob_win``/``prob_top2``/``prob_top3``/``lambdarank_score``.
    """
    from src.model.client import ModalClient

    path, err = _kyi_path_for(race.held_on)
    if path is None:
        return 0, err

    kyi_df = parse_file(path, KYI_FIELDS, KYI_RECORD_LENGTH)
    feats = build_prediction_features(kyi_df)
    race_feats = feats[feats["race_key"] == race.race_key].copy()
    if race_feats.empty:
        return 0, f"No KYI rows for race_key={race.race_key}"

    feature_cols = [c for c in race_feats.columns if c not in ("race_key", "horse_name", "fukusho_odds")]
    payload = race_feats[feature_cols].to_dict("records")

    client = ModalClient()
    result = client.predict(payload)
    if not result.get("success"):
        return 0, str(result.get("error", "predict failed"))

    probs = result["predictions"]
    race_feats["prob"] = probs
    race_feats["odds_num"] = pd.to_numeric(race_feats.get("odds"), errors="coerce")
    race_feats["fuku_num"] = pd.to_numeric(race_feats.get("fukusho_odds"), errors="coerce")
    race_feats["ev_tan"] = (race_feats["prob"] / 3.0) * race_feats["odds_num"]
    race_feats["ev_fuku"] = race_feats["prob"] * race_feats["fuku_num"]

    # Phase 2: optionally call lambdarank if the model is deployed.
    lambdarank_payload: dict | None = None
    try:
        lambdarank_payload = client.predict_lambdarank(payload)
        if not lambdarank_payload.get("success"):
            lambdarank_payload = None
    except Exception:
        lambdarank_payload = None

    if lambdarank_payload:
        race_feats["lambdarank_score"] = lambdarank_payload.get("scores", [None] * len(race_feats))
        race_feats["prob_win"] = lambdarank_payload.get("prob_win", [None] * len(race_feats))
        race_feats["prob_top2"] = lambdarank_payload.get("prob_top2", [None] * len(race_feats))
        # lambdarank's prob_top3 (PL-derived) is one option; AutoGluon's prob is
        # already a calibrated top-3 prob — keep AutoGluon's in `prob_top3`.
        race_feats["prob_top3"] = race_feats["prob"]

    now = datetime.utcnow()
    horses_by_no = {h.horse_number: h for h in race.horses}

    written = 0
    for _, row in race_feats.iterrows():
        hn = int(row["horse_number"])
        horse = horses_by_no.get(hn)
        if horse is None:
            continue

        def _opt(col: str) -> float | None:
            val = row.get(col)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return None
            return float(val)

        pred = session.scalar(
            select(Prediction).where(
                Prediction.horse_entry_id == horse.id,
                Prediction.model_version == model_version,
            )
        )
        kwargs = {
            "prob": float(row["prob"]),
            "ev_tan": _opt("ev_tan"),
            "ev_fuku": _opt("ev_fuku"),
            "prob_win": _opt("prob_win"),
            "prob_top2": _opt("prob_top2"),
            "prob_top3": _opt("prob_top3"),
            "lambdarank_score": _opt("lambdarank_score"),
            "predicted_at": now,
        }
        if pred is None:
            session.add(Prediction(
                horse_entry_id=horse.id,
                model_version=model_version,
                **kwargs,
            ))
        else:
            for k, v in kwargs.items():
                setattr(pred, k, v)
        written += 1

    return written, ""


@router.post("/{race_key}/predict", response_model=PredictResponse)
def predict_race(race_key: str, session: DbSession) -> PredictResponse:
    race = session.scalar(
        select(Race)
        .where(Race.race_key == race_key)
        .options(selectinload(Race.horses).selectinload(HorseEntry.predictions))
    )
    if race is None:
        raise HTTPException(status_code=404, detail=f"Race not found: {race_key}")

    model_version = _resolve_model_version()
    started = time.perf_counter()
    written, err = _predict_one(session, race, model_version)
    if err:
        raise HTTPException(status_code=502, detail=err)
    if written == 0:
        raise HTTPException(status_code=500, detail="No predictions written")
    session.commit()
    session.refresh(race)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    latest_by_horse = {
        h.id: max(h.predictions, key=lambda p: p.predicted_at)
        for h in race.horses if h.predictions
    }
    horses = [
        _horse_to_schema(h, latest_by_horse.get(h.id))
        for h in sorted(race.horses, key=lambda h: h.horse_number)
    ]
    predicted_at = max((p.predicted_at for p in latest_by_horse.values()), default=datetime.utcnow())

    return PredictResponse(
        race_key=race_key,
        horses=horses,
        model_version=model_version,
        predicted_at=predicted_at,
        elapsed_ms=elapsed_ms,
    )


class MultibetQuery(BaseModel):
    ev_threshold: float = 1.10
    max_bets: int = 10


class MultibetPick(BaseModel):
    key: str
    combo: list[int] | None = None
    horse: int | None = None
    prob: float
    odds: float
    ev: float


class MultibetResponse(BaseModel):
    race_key: str
    ev_threshold: float
    tan: list[MultibetPick]
    fuku: list[MultibetPick]
    wide: list[MultibetPick]
    umatan: list[MultibetPick]
    sanrenpuku: list[MultibetPick]


def _row_to_pick(r: dict) -> MultibetPick:
    return MultibetPick(
        key=str(r.get("key") or r.get("horse")),
        combo=list(r["combo"]) if "combo" in r else None,
        horse=int(r["horse"]) if "horse" in r else None,
        prob=float(r["prob"]),
        odds=float(r["odds"]),
        ev=float(r["ev"]),
    )


@router.get("/{race_key}/multibet", response_model=MultibetResponse)
def race_multibet(
    race_key: str,
    session: DbSession,
    ev_threshold: float = 1.10,
    max_bets: int = 10,
) -> MultibetResponse:
    """Phase 4 multibet EVs (single/place/wide/umatan/sanrenpuku) for a race.

    Reads pre-race odds (from race_odds, ingested via OW/OU/OT) and the
    latest predictions (prob_win from lambdarank if available; falls back to
    prob/3 from AutoGluon)."""
    from src.db.models import HorseEntry, RaceOdds
    from src.predict.multibet import (
        compute_fuku_ev,
        compute_sanrenpuku_ev,
        compute_tan_ev,
        compute_umatan_ev,
        compute_wide_ev,
        recommend_threshold,
    )

    race = session.scalar(
        select(Race)
        .where(Race.race_key == race_key)
        .options(selectinload(Race.horses).selectinload(HorseEntry.predictions))
    )
    if race is None:
        raise HTTPException(status_code=404, detail=f"Race not found: {race_key}")

    horses = sorted(race.horses, key=lambda h: h.horse_number)
    horse_numbers = [int(h.horse_number) for h in horses]
    odds_tan = {int(h.horse_number): float(h.odds) for h in horses if h.odds}
    odds_fuku = {
        int(h.horse_number): float(h.fukusho_odds)
        for h in horses if h.fukusho_odds
    }

    prob_win: list[float] = []
    prob_top3: list[float] = []
    for h in horses:
        preds = sorted(h.predictions, key=lambda p: p.predicted_at, reverse=True)
        latest = preds[0] if preds else None
        if latest is None:
            prob_win.append(0.0)
            prob_top3.append(0.0)
        else:
            pw = latest.prob_win if latest.prob_win is not None else (latest.prob / 3.0)
            pt3 = latest.prob_top3 if latest.prob_top3 is not None else latest.prob
            prob_win.append(float(pw))
            prob_top3.append(float(pt3))

    odds_row = session.scalar(
        select(RaceOdds).where(RaceOdds.race_id == race.id)
    )

    tan = compute_tan_ev(horse_numbers, prob_win, odds_tan)
    fuku = compute_fuku_ev(horse_numbers, prob_top3, odds_fuku)
    wide_picks: list[dict] = []
    umatan_picks: list[dict] = []
    sanren_picks: list[dict] = []
    if odds_row is not None:
        if odds_row.wide:
            wide_picks = compute_wide_ev(horse_numbers, prob_win, odds_row.wide)
        if odds_row.umatan:
            umatan_picks = compute_umatan_ev(horse_numbers, prob_win, odds_row.umatan)
        if odds_row.sanrenpuku:
            sanren_picks = compute_sanrenpuku_ev(horse_numbers, prob_win, odds_row.sanrenpuku)

    def _picks(rows: list[dict]) -> list[MultibetPick]:
        return [_row_to_pick(r) for r in recommend_threshold(rows, ev_threshold, max_bets)]

    return MultibetResponse(
        race_key=race_key,
        ev_threshold=ev_threshold,
        tan=_picks(tan),
        fuku=_picks(fuku),
        wide=_picks(wide_picks),
        umatan=_picks(umatan_picks),
        sanrenpuku=_picks(sanren_picks),
    )


@router.post("/predict-batch", response_model=PredictBatchResponse)
def predict_batch(req: PredictBatchRequest, session: DbSession) -> PredictBatchResponse:
    races = session.scalars(
        select(Race)
        .where(Race.held_on == req.date)
        .options(selectinload(Race.horses))
        .order_by(Race.venue_code, Race.race_no)
    ).all()
    if not races:
        raise HTTPException(status_code=404, detail=f"No races for date {req.date}")

    model_version = _resolve_model_version()
    started = time.perf_counter()
    jobs: list[PredictBatchItem] = []

    for race in races:
        try:
            written, err = _predict_one(session, race, model_version)
            if err:
                jobs.append(PredictBatchItem(race_key=race.race_key, status="error", error=err))
            elif written == 0:
                jobs.append(PredictBatchItem(race_key=race.race_key, status="skipped"))
            else:
                jobs.append(PredictBatchItem(race_key=race.race_key, status="ok"))
        except Exception as e:
            jobs.append(PredictBatchItem(race_key=race.race_key, status="error", error=str(e)))
        session.commit()

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return PredictBatchResponse(jobs=jobs, elapsed_ms=elapsed_ms)
