"""Boonta v2 configuration via environment variables and .env file."""
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # JRDB credentials
    jrdb_user: str = ""
    jrdb_pass: str = ""
    jrdb_base_url: str = "http://www.jrdb.com/member/datazip/"

    # Paths
    project_root: Path = Path(__file__).parent.parent
    data_raw_dir: Path = project_root / "data" / "raw"
    data_processed_dir: Path = project_root / "data" / "processed"

    # Modal
    modal_app_name: str = "boonta-ml"
    modal_volume_name: str = "boonta-models"
    model_name: str = "jrdb_predictor"

    # Training
    autogluon_time_limit: int = 1800
    autogluon_presets: str = "best_quality"

    model_config = {"env_file": ".env", "env_prefix": ""}
