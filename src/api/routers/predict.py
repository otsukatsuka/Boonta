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
from src.api.schemas import (
    Horse,
    PredictBatchItem,
    PredictBatchResponse,
    PredictResponse,
)
from src.api.routers.races import _horse_to_schema
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
    """Run prediction for one race; upsert prediction rows. Returns (count, error)."""
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

    now = datetime.utcnow()
    horses_by_no = {h.horse_number: h for h in race.horses}

    written = 0
    for _, row in race_feats.iterrows():
        hn = int(row["horse_number"])
        horse = horses_by_no.get(hn)
        if horse is None:
            continue

        ev_tan = row["ev_tan"]
        ev_fuku = row["ev_fuku"]
        pred = session.scalar(
            select(Prediction).where(
                Prediction.horse_entry_id == horse.id,
                Prediction.model_version == model_version,
            )
        )
        if pred is None:
            session.add(Prediction(
                horse_entry_id=horse.id,
                model_version=model_version,
                prob=float(row["prob"]),
                ev_tan=None if pd.isna(ev_tan) else float(ev_tan),
                ev_fuku=None if pd.isna(ev_fuku) else float(ev_fuku),
                predicted_at=now,
            ))
        else:
            pred.prob = float(row["prob"])
            pred.ev_tan = None if pd.isna(ev_tan) else float(ev_tan)
            pred.ev_fuku = None if pd.isna(ev_fuku) else float(ev_fuku)
            pred.predicted_at = now
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
