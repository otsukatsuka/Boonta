"""API routers."""

from app.api.entries import router as entries_router
from app.api.fetch import router as fetch_router
from app.api.horses import router as horses_router
from app.api.jockeys import router as jockeys_router
from app.api.model import router as model_router
from app.api.predictions import router as predictions_router
from app.api.races import router as races_router

__all__ = [
    "races_router",
    "horses_router",
    "jockeys_router",
    "entries_router",
    "predictions_router",
    "fetch_router",
    "model_router",
]
