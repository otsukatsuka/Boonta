"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "Boonta"
    app_version: str = "0.1.0"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./data/boonta.db"

    # ML Model
    model_path: Path = Path("models")
    model_version: str = "v2.0.0-ml"  # AutoGluon ML model integrated

    # Scraping
    scraping_delay: float = 1.0  # seconds between requests
    user_agent: str = "Mozilla/5.0 (compatible; BoontaBot/1.0)"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
