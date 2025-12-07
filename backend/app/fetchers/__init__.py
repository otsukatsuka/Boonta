"""External data fetchers."""

from app.fetchers.base import DataFetcher, EntryInfo, RaceInfo, ResultInfo
from app.fetchers.netkeiba import NetkeibaFetcher

__all__ = [
    "DataFetcher",
    "RaceInfo",
    "EntryInfo",
    "ResultInfo",
    "NetkeibaFetcher",
]
