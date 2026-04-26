from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TrainingRunOut(BaseModel):
    id: int
    run_id: str
    trained_at: datetime
    preset: str
    logloss: Optional[float] = None
    auc: Optional[float] = None
    brier: Optional[float] = None
    hit_at_3: Optional[float] = None
    train_time_seconds: Optional[int] = None
    num_samples: Optional[int] = None
    status: str


class LeaderboardRow(BaseModel):
    model: str
    score_val: Optional[float] = None
    eval_metric: Optional[str] = None
    fit_time: Optional[float] = None
    weight: Optional[float] = None


class LeaderboardResponse(BaseModel):
    run_id: Optional[str] = None
    rows: list[LeaderboardRow]


class FeatureImportanceRow(BaseModel):
    name: str
    jp_label: Optional[str] = None
    importance: float


class CalibrationBin(BaseModel):
    pred_mid: float
    actual_rate: float
    n: int


class CalibrationResponse(BaseModel):
    run_id: Optional[str] = None
    bins: list[CalibrationBin]
    ece: Optional[float] = None
    mce: Optional[float] = None
    n_total: int
    window_from: Optional[date] = None
    window_to: Optional[date] = None


class ModelStatusOut(BaseModel):
    deployed_run_id: Optional[str] = None
    trained_at: Optional[datetime] = None
    num_samples: Optional[int] = None
    best_score: Optional[float] = None
    preset: Optional[str] = None
    modal_ready: bool
