from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SystemStatus(BaseModel):
    jrdb_sync: Optional[datetime]
    modal_ready: bool
    model_name: str
    model_version: Optional[str]
    feature_count: int
    ev_threshold_default: float
    preset: str
