from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


FeedStatus = Literal["OK", "WARN", "NA"]


class FeedRow(BaseModel):
    id: str
    name: str
    status: FeedStatus
    bytes: Optional[int] = None
    rows: Optional[int] = None
    last_iso: Optional[datetime] = None
    lag_minutes: Optional[int] = None


class FeedsResponse(BaseModel):
    feeds: list[FeedRow]
    total_bytes: int
    total_rows: int
    ok_count: int
    total_count: int
    latest_iso: Optional[datetime] = None


class CoverageResponse(BaseModel):
    years: list[int]
    counts: list[list[int]]


class FeatureMeta(BaseModel):
    name: str
    jp_label: Optional[str] = None
    type: Literal["num", "cat"]
    importance: Optional[float] = None


class FeatureStat(BaseModel):
    name: str
    type: Literal["num", "cat"]
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    missing_pct: Optional[float] = None
    cardinality: Optional[int] = None
