from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class EquityPoint(BaseModel):
    month: str          # "YYYY-MM"
    cum: int            # cumulative PnL


class Strategy(BaseModel):
    run_id: int
    id: str             # strategy name (ev_tansho etc.)
    label: str
    kind: str           # "ML" | "EV"
    date_from: date
    date_to: date
    ev_threshold: Optional[float]
    model_version: str
    races: int
    bet_races: int
    invested: int
    returned: int
    hits: int
    roi: float
    equity: list[EquityPoint]
    computed_at: datetime


class SensitivityRow(BaseModel):
    thr: float
    bet_races: Optional[int]
    hits: Optional[int]
    roi: Optional[float]


class BacktestRunRequest(BaseModel):
    strategy: str = "all"
    date_from: date
    date_to: date
    ev_threshold: float = 1.0
    sensitivity: bool = True


class BacktestRunResponse(BaseModel):
    runs: list[Strategy]
    elapsed_ms: int
