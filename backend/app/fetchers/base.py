"""Base data fetcher."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.config import get_settings

settings = get_settings()


@dataclass
class RaceInfo:
    """Race information from external source."""

    external_id: str
    name: str
    date: str  # YYYY-MM-DD
    venue: str
    course_type: str
    distance: int
    grade: str
    track_condition: str | None = None
    weather: str | None = None
    purse: int | None = None


@dataclass
class EntryInfo:
    """Entry information from external source."""

    horse_name: str
    horse_number: int
    post_position: int
    jockey_name: str
    weight: float
    odds: float | None = None
    popularity: int | None = None
    horse_weight: int | None = None
    horse_weight_diff: int | None = None
    trainer: str | None = None


@dataclass
class ResultInfo:
    """Race result information from external source."""

    race_name: str
    race_date: str
    venue: str
    distance: int
    course_type: str
    position: int
    time: float | None = None
    margin: str | None = None
    last_3f: float | None = None
    jockey_name: str | None = None
    weight: float | None = None
    track_condition: str | None = None
    corner_positions: list[int] | None = None  # コーナー通過順
    popularity: int | None = None


@dataclass
class OddsInfo:
    """Odds information for a race entry."""

    horse_number: int
    odds: float
    popularity: int
    corner_positions: list[int] | None = None  # コーナー通過順
    running_style: str | None = None  # 推定脚質


@dataclass
class ShutubaOddsInfo:
    """Odds and popularity from shutuba (pre-race) page."""

    horse_number: int
    horse_name: str
    odds: float | None
    popularity: int | None


class DataFetcher(ABC):
    """Base class for external data fetchers."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent},
            timeout=30.0,
            follow_redirects=True,
        )
        self.delay = settings.scraping_delay

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @abstractmethod
    async def fetch_race_info(self, race_id: str) -> RaceInfo | None:
        """Fetch race basic information."""
        pass

    @abstractmethod
    async def fetch_entries(self, race_id: str) -> list[EntryInfo]:
        """Fetch entry information for a race."""
        pass

    @abstractmethod
    async def fetch_horse_results(
        self, horse_id: str, limit: int = 10
    ) -> list[ResultInfo]:
        """Fetch past results for a horse."""
        pass
