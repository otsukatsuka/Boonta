"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import backtest, predict, races, system

app = FastAPI(title="Boonta WebUI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/api")
app.include_router(races.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"ok": True}
