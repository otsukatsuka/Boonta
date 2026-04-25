"""System status (JRDB sync, Modal model)."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from src.api.deps import DbSession
from src.api.schemas import SystemStatus
from src.db.models import Race
from src.features.columns import FEATURE_COLUMNS

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatus)
def get_status(session: DbSession) -> SystemStatus:
    last_sync = session.scalar(select(func.max(Race.ingested_at)))

    # Modal status — best-effort, never block API on cold-start.
    modal_ready = False
    model_version: str | None = None
    try:
        from src.model.client import ModalClient

        client = ModalClient()
        info = client.get_model_status()
        if isinstance(info, dict) and info.get("exists"):
            modal_ready = True
            trained = info.get("trained_at")
            if trained:
                model_version = str(trained)[:10]
    except Exception:
        modal_ready = False

    from config.settings import Settings

    s = Settings()
    return SystemStatus(
        jrdb_sync=last_sync,
        modal_ready=modal_ready,
        model_name=s.model_name,
        model_version=model_version,
        feature_count=len(FEATURE_COLUMNS),
        ev_threshold_default=1.0,
        preset=s.autogluon_presets,
    )
