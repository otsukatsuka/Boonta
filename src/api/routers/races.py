"""Race list and detail endpoints (read-only — predictions are in /predict.py)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.api import labels
from src.api.deps import DbSession
from src.api.schemas import Horse, MlTop, RaceDetail, RaceListItem
from src.db.models import HorseEntry, Prediction, Race

router = APIRouter(prefix="/races", tags=["races"])


def _horse_to_schema(h: HorseEntry, pred: Prediction | None) -> Horse:
    return Horse(
        horse_number=h.horse_number,
        waku=h.waku,
        name=h.name,
        jockey=h.jockey,
        jockey_index=h.jockey_index,
        weight_carried=h.weight_carried,
        running_style=h.running_style,
        idm=h.idm,
        mid_position=h.mid_position,
        late3f_position=h.late3f_position,
        goal_position=h.goal_position,
        goal_io=h.goal_io,
        odds=h.odds,
        fukusho_odds=h.fukusho_odds,
        popularity=h.popularity,
        gate_miss_rate=h.gate_miss_rate,
        upset_index=h.upset_index,
        prob=pred.prob if pred else None,
        ev_tan=pred.ev_tan if pred else None,
        ev_fuku=pred.ev_fuku if pred else None,
    )


def _race_to_list_item(race: Race) -> RaceListItem:
    """Build RaceListItem with best-EV / ml-top derived from latest predictions."""
    best_ev_tan: float | None = None
    best_ev_fuku: float | None = None
    ml_top: MlTop | None = None

    # Latest prediction per horse (one model_version assumed; if multiple, take last).
    latest_by_horse: dict[int, Prediction] = {}
    for h in race.horses:
        for p in h.predictions:
            cur = latest_by_horse.get(h.id)
            if cur is None or (p.predicted_at and p.predicted_at > cur.predicted_at):
                latest_by_horse[h.id] = p

    if latest_by_horse:
        ranked = sorted(
            race.horses,
            key=lambda h: latest_by_horse[h.id].prob if h.id in latest_by_horse else -1,
            reverse=True,
        )
        top = ranked[0]
        top_pred = latest_by_horse.get(top.id)
        if top_pred:
            ml_top = MlTop(horse_number=top.horse_number, name=top.name, prob=top_pred.prob)
            evs_tan = [p.ev_tan for p in latest_by_horse.values() if p.ev_tan is not None]
            evs_fuku = [p.ev_fuku for p in latest_by_horse.values() if p.ev_fuku is not None]
            best_ev_tan = max(evs_tan) if evs_tan else None
            best_ev_fuku = max(evs_fuku) if evs_fuku else None
            status = "DONE"
        else:
            status = "NO_PREDICTION"
    else:
        status = "NO_PREDICTION"

    horses = [
        _horse_to_schema(h, latest_by_horse.get(h.id))
        for h in sorted(race.horses, key=lambda x: x.horse_number)
    ]

    return RaceListItem(
        race_key=race.race_key,
        held_on=race.held_on,
        venue_code=race.venue_code,
        venue=race.venue,
        race_no=race.race_no,
        name=race.name,
        grade=labels.label(labels.GRADE, race.grade),
        surface=labels.label(labels.SURFACE, race.surface),
        distance=race.distance,
        condition=labels.label(labels.CONDITION, race.condition),
        weather=labels.label(labels.WEATHER, race.weather),
        post_time=race.post_time,
        head_count=race.head_count,
        pace=race.pace_forecast,
        best_ev_tan=best_ev_tan,
        best_ev_fuku=best_ev_fuku,
        ml_top=ml_top,
        status=status,
        horses=horses,
    )


@router.get("", response_model=list[RaceListItem])
def list_races(
    session: DbSession,
    date_: date = Query(..., alias="date"),
) -> list[RaceListItem]:
    races = session.scalars(
        select(Race)
        .where(Race.held_on == date_)
        .options(selectinload(Race.horses).selectinload(HorseEntry.predictions))
        .order_by(Race.venue_code, Race.race_no)
    ).all()
    return [_race_to_list_item(r) for r in races]


@router.get("/{race_key}", response_model=RaceDetail)
def get_race(race_key: str, session: DbSession) -> RaceDetail:
    race = session.scalar(
        select(Race)
        .where(Race.race_key == race_key)
        .options(selectinload(Race.horses).selectinload(HorseEntry.predictions))
    )
    if race is None:
        raise HTTPException(status_code=404, detail=f"Race not found: {race_key}")

    latest_by_horse: dict[int, Prediction] = {}
    for h in race.horses:
        for p in h.predictions:
            cur = latest_by_horse.get(h.id)
            if cur is None or (p.predicted_at and p.predicted_at > cur.predicted_at):
                latest_by_horse[h.id] = p

    horses = [
        _horse_to_schema(h, latest_by_horse.get(h.id))
        for h in sorted(race.horses, key=lambda h: h.horse_number)
    ]

    updated_at = max((p.predicted_at for p in latest_by_horse.values()), default=None)

    return RaceDetail(
        race=_race_to_list_item(race),
        horses=horses,
        updated_at=updated_at,
    )
