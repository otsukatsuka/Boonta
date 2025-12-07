"""Data access repositories."""

from app.repositories.base import BaseRepository
from app.repositories.entry_repository import EntryRepository
from app.repositories.horse_repository import HorseRepository
from app.repositories.jockey_repository import JockeyRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.race_repository import RaceRepository
from app.repositories.result_repository import ResultRepository

__all__ = [
    "BaseRepository",
    "RaceRepository",
    "HorseRepository",
    "JockeyRepository",
    "EntryRepository",
    "ResultRepository",
    "PredictionRepository",
]
