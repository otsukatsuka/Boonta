"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    entries_router,
    fetch_router,
    horses_router,
    jockeys_router,
    model_router,
    predictions_router,
    races_router,
)
from app.config import get_settings
from app.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Horse Racing Prediction AI Service",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Register API routers
app.include_router(races_router, prefix="/api")
app.include_router(horses_router, prefix="/api")
app.include_router(jockeys_router, prefix="/api")
app.include_router(entries_router, prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(fetch_router, prefix="/api")
app.include_router(model_router, prefix="/api")
