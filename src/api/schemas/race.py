from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class MlTop(BaseModel):
    horse_number: int
    name: str
    prob: float


class RaceListItem(BaseModel):
    race_key: str
    held_on: date
    venue_code: str
    venue: str
    race_no: int
    name: Optional[str]
    grade: Optional[str]
    surface: Optional[str]
    distance: Optional[int]
    condition: Optional[str]
    weather: Optional[str]
    post_time: Optional[str]
    head_count: Optional[int]
    pace: Optional[str]                      # H|M|S
    best_ev_tan: Optional[float]
    best_ev_fuku: Optional[float]
    ml_top: Optional[MlTop]
    status: str                              # OPEN | DONE | NO_PREDICTION


class Horse(BaseModel):
    horse_number: int
    waku: Optional[int]
    name: str
    jockey: Optional[str]
    jockey_index: Optional[float]
    weight_carried: Optional[float]
    running_style: Optional[int]
    idm: Optional[float]
    mid_position: Optional[int]
    late3f_position: Optional[int]
    goal_position: Optional[int]
    goal_io: Optional[int]
    odds: Optional[float]
    fukusho_odds: Optional[float]
    popularity: Optional[int]
    gate_miss_rate: Optional[float]
    upset_index: Optional[int]
    prob: Optional[float]
    ev_tan: Optional[float]
    ev_fuku: Optional[float]


class RaceDetail(BaseModel):
    race: RaceListItem
    horses: list[Horse]
    updated_at: Optional[datetime]


class PredictResponse(BaseModel):
    race_key: str
    horses: list[Horse]
    model_version: str
    predicted_at: datetime
    elapsed_ms: int


class PredictBatchItem(BaseModel):
    race_key: str
    status: str                              # ok | error | skipped
    error: Optional[str] = None


class PredictBatchResponse(BaseModel):
    jobs: list[PredictBatchItem]
    elapsed_ms: int
