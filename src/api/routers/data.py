"""DATA tab — JRDB feeds, dataset coverage, KYI feature inspector."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError

from config.settings import Settings
from src.api.deps import DbSession
from src.api.schemas import (
    CoverageResponse,
    FeatureMeta,
    FeatureStat,
    FeedRow,
    FeedsResponse,
)
from src.db.models import HorseEntry, Race
from src.features.columns import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    FIELD_TO_FEATURE,
)

router = APIRouter(prefix="/system", tags=["data"])

SUPPORTED_FEEDS = ("KYI", "SED", "HJC", "BAC")
ALL_FEEDS = (
    ("KYI", "出馬表 (KYI)"),
    ("SED", "成績 (SED)"),
    ("HJC", "払戻 (HJC)"),
    ("BAC", "番組表 (BAC)"),
    ("CHA", "調教 (CHA)"),
    ("CYB", "調教コメ (CYB)"),
    ("KAB", "開催 (KAB)"),
    ("OZ", "オッズ (OZ)"),
)


_LINE_COUNT_CACHE: dict[tuple[str, float], int] = {}


def _count_lines(path: Path, mtime: float) -> int:
    key = (str(path), mtime)
    cached = _LINE_COUNT_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        with path.open("rb") as f:
            n = sum(1 for _ in f)
    except OSError:
        n = 0
    _LINE_COUNT_CACHE[key] = n
    return n


@router.get("/feeds", response_model=FeedsResponse)
def get_feeds() -> FeedsResponse:
    settings = Settings()
    raw_dir: Path = settings.data_raw_dir
    rows: list[FeedRow] = []
    total_bytes = 0
    total_rows = 0
    ok_count = 0
    latest_iso: Optional[datetime] = None

    for feed_id, name in ALL_FEEDS:
        if feed_id not in SUPPORTED_FEEDS:
            rows.append(FeedRow(id=feed_id, name=name, status="NA"))
            continue

        files = sorted(raw_dir.glob(f"{feed_id}*.txt"), key=lambda p: p.stat().st_mtime)
        if not files:
            rows.append(FeedRow(id=feed_id, name=name, status="WARN"))
            continue

        latest = files[-1]
        st = latest.stat()
        mtime_dt = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        lag_minutes = max(0, int((time.time() - st.st_mtime) / 60))
        line_count = _count_lines(latest, st.st_mtime)

        rows.append(
            FeedRow(
                id=feed_id,
                name=name,
                status="OK",
                bytes=st.st_size,
                rows=line_count,
                last_iso=mtime_dt,
                lag_minutes=lag_minutes,
            )
        )
        total_bytes += st.st_size
        total_rows += line_count
        ok_count += 1
        if latest_iso is None or mtime_dt > latest_iso:
            latest_iso = mtime_dt

    return FeedsResponse(
        feeds=rows,
        total_bytes=total_bytes,
        total_rows=total_rows,
        ok_count=ok_count,
        total_count=len(ALL_FEEDS),
        latest_iso=latest_iso,
    )


@router.get("/coverage", response_model=CoverageResponse)
def get_coverage(
    session: DbSession,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
) -> CoverageResponse:
    bounds = session.execute(
        select(func.min(Race.held_on), func.max(Race.held_on))
    ).one()
    min_d, max_d = bounds
    if from_year is None:
        from_year = min_d.year if min_d else datetime.now().year
    if to_year is None:
        to_year = max_d.year if max_d else datetime.now().year

    rows = session.execute(
        text(
            "SELECT CAST(strftime('%Y', held_on) AS INTEGER) y, "
            "CAST(strftime('%m', held_on) AS INTEGER) m, COUNT(*) c "
            "FROM race GROUP BY y, m"
        )
    ).all()

    grid: dict[int, list[int]] = {y: [0] * 12 for y in range(from_year, to_year + 1)}
    for y, m, c in rows:
        if y in grid and 1 <= m <= 12:
            grid[y][m - 1] = c

    years = list(range(from_year, to_year + 1))
    counts = [grid[y] for y in years]
    return CoverageResponse(years=years, counts=counts)


def _reverse_label_lookup() -> dict[str, str]:
    return {ml: jp for jp, ml in FIELD_TO_FEATURE.items()}


@router.get("/features", response_model=list[FeatureMeta])
def get_features() -> list[FeatureMeta]:
    rev = _reverse_label_lookup()
    out: list[FeatureMeta] = []
    for name in FEATURE_COLUMNS:
        out.append(
            FeatureMeta(
                name=name,
                jp_label=rev.get(name),
                type="cat" if name in CATEGORICAL_FEATURES else "num",
            )
        )
    return out


# Maps ML feature name → DB column on HorseEntry where that value is stored.
HORSE_ENTRY_COL: dict[str, str] = {
    "idm": "idm",
    "jockey_index": "jockey_index",
    "weight_carried": "weight_carried",
    "popularity": "popularity",
    "odds": "odds",
    "gate_miss_rate": "gate_miss_rate",
    "upset_index": "upset_index",
    "mid_position": "mid_position",
    "late3f_position": "late3f_position",
    "goal_position": "goal_position",
    "goal_io": "goal_io",
    "running_style": "running_style",
    "waku": "waku",
    "horse_number": "horse_number",
}


_FEATURE_STATS_CACHE: dict[str, tuple[float, list[FeatureStat]]] = {}
_FEATURE_STATS_TTL = 600.0


@router.get("/feature-stats", response_model=list[FeatureStat])
def get_feature_stats(session: DbSession) -> list[FeatureStat]:
    cached = _FEATURE_STATS_CACHE.get("all")
    if cached and (time.time() - cached[0]) < _FEATURE_STATS_TTL:
        return cached[1]

    total = session.scalar(select(func.count()).select_from(HorseEntry)) or 0
    out: list[FeatureStat] = []

    for name in FEATURE_COLUMNS:
        ftype: str = "cat" if name in CATEGORICAL_FEATURES else "num"
        col = HORSE_ENTRY_COL.get(name)
        if not col or total == 0:
            out.append(FeatureStat(name=name, type=ftype, missing_pct=None))
            continue

        if ftype == "num":
            try:
                row = session.execute(
                    text(
                        f"SELECT MIN({col}) mn, MAX({col}) mx, AVG({col}) avg, "
                        f"SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) nulls, "
                        f"COUNT({col}) non_nulls FROM horse_entry"
                    )
                ).one()
                mn, mx, avg, nulls, non_nulls = row
                std: Optional[float] = None
                if non_nulls and avg is not None:
                    var_row = session.execute(
                        text(
                            f"SELECT AVG(({col} - :avg) * ({col} - :avg)) "
                            f"FROM horse_entry WHERE {col} IS NOT NULL"
                        ),
                        {"avg": float(avg)},
                    ).scalar()
                    if var_row is not None and var_row >= 0:
                        std = float(var_row) ** 0.5
                missing_pct = float(nulls) / float(total) * 100.0 if total else None
                out.append(
                    FeatureStat(
                        name=name,
                        type=ftype,
                        min=float(mn) if mn is not None else None,
                        max=float(mx) if mx is not None else None,
                        mean=float(avg) if avg is not None else None,
                        std=std,
                        missing_pct=missing_pct,
                    )
                )
            except OperationalError:
                out.append(FeatureStat(name=name, type=ftype, missing_pct=None))
        else:
            try:
                card_row = session.execute(
                    text(f"SELECT COUNT(DISTINCT {col}) FROM horse_entry")
                ).scalar()
                nulls_row = session.execute(
                    text(
                        f"SELECT SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) "
                        f"FROM horse_entry"
                    )
                ).scalar()
                missing_pct = (
                    float(nulls_row or 0) / float(total) * 100.0 if total else None
                )
                out.append(
                    FeatureStat(
                        name=name,
                        type=ftype,
                        cardinality=int(card_row) if card_row is not None else None,
                        missing_pct=missing_pct,
                    )
                )
            except OperationalError:
                out.append(FeatureStat(name=name, type=ftype, missing_pct=None))

    _FEATURE_STATS_CACHE["all"] = (time.time(), out)
    return out
