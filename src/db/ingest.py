"""Ingest parsed JRDB DataFrames into the database (UPSERT)."""
from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import HjcPayout, HorseEntry, Race
from src.parser.engine import build_race_key


def _merge_source(existing: str | None, new: str) -> str:
    parts = set((existing or "").split("+")) - {""}
    parts.add(new)
    return "+".join(sorted(parts))

VENUE_NAMES: dict[str, str] = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
    "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉",
}


def held_on_from_filename(path: Path) -> date:
    """Decode held_on date from KYI/SED/HJC filename like KYI200405.txt → 2020-04-05.

    Two-digit year: <70 → 20YY, otherwise 19YY (covers 1970-2069).
    """
    digits = path.stem[3:]  # KYI200405 → 200405
    if len(digits) != 6 or not digits.isdigit():
        raise ValueError(f"Cannot decode date from filename: {path.name}")
    yy = int(digits[:2])
    year = 2000 + yy if yy < 70 else 1900 + yy
    return date(year, int(digits[2:4]), int(digits[4:6]))


def _to_int(value) -> int | None:
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f):
            return None
        return int(f)
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _to_str(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    s = str(value).strip()
    return s or None


def _mode(series: pd.Series) -> str | None:
    """Most common non-empty string in a Series, or None."""
    cleaned = series.dropna().astype(str).str.strip()
    cleaned = cleaned[cleaned != ""]
    if cleaned.empty:
        return None
    return cleaned.mode().iloc[0]


def ingest_kyi(session: Session, df: pd.DataFrame, held_on: date) -> int:
    """Upsert KYI DataFrame into race + horse_entry. Returns # races touched."""
    if df.empty:
        return 0

    df = df.copy()
    df["race_key"] = df.apply(lambda r: build_race_key(r.to_dict()), axis=1)
    now = datetime.utcnow()
    races_touched = 0

    for race_key, group in df.groupby("race_key"):
        first = group.iloc[0]
        venue_code = f"{_to_int(first.get('場コード')) or 0:02d}"
        race_no = _to_int(first.get("R")) or 0
        head_count = len(group)
        pace = _mode(group.get("ペース予想", pd.Series(dtype=str)))

        race = session.scalar(select(Race).where(Race.race_key == race_key))
        if race is None:
            race = Race(
                race_key=str(race_key),
                held_on=held_on,
                venue_code=venue_code,
                venue=VENUE_NAMES.get(venue_code, venue_code),
                race_no=race_no,
                head_count=head_count,
                pace_forecast=pace,
                source="KYI",
                ingested_at=now,
            )
            session.add(race)
            session.flush()  # populate race.id
        else:
            race.held_on = held_on
            race.venue_code = venue_code
            race.venue = VENUE_NAMES.get(venue_code, venue_code)
            race.race_no = race_no
            race.head_count = head_count
            race.pace_forecast = pace
            race.source = _merge_source(race.source, "KYI")
            race.ingested_at = now

        races_touched += 1

        # Map existing horses by horse_number for UPSERT
        existing = {h.horse_number: h for h in race.horses}

        for _, row in group.iterrows():
            horse_number = _to_int(row.get("馬番"))
            if horse_number is None:
                continue

            weight_raw = _to_float(row.get("負担重量"))
            weight_kg = weight_raw / 10.0 if weight_raw is not None else None

            data = dict(
                horse_number=horse_number,
                waku=_to_int(row.get("枠番")),
                name=_to_str(row.get("馬名")) or "",
                jockey=_to_str(row.get("騎手名")),
                jockey_index=_to_float(row.get("騎手指数")),
                weight_carried=weight_kg,
                running_style=_to_int(row.get("脚質")),
                idm=_to_float(row.get("IDM")),
                mid_position=_to_int(row.get("道中順位")),
                late3f_position=_to_int(row.get("後3F順位")),
                goal_position=_to_int(row.get("ゴール順位")),
                goal_io=_to_int(row.get("ゴール内外")),
                odds=_to_float(row.get("基準オッズ")),
                fukusho_odds=_to_float(row.get("基準複勝オッズ")),
                popularity=_to_int(row.get("基準人気順位")),
                gate_miss_rate=_to_float(row.get("馬出遅率")),
                upset_index=_to_int(row.get("万券指数")),
            )

            entry = existing.get(horse_number)
            if entry is None:
                entry = HorseEntry(race_id=race.id, **data)
                session.add(entry)
            else:
                for k, v in data.items():
                    setattr(entry, k, v)

    return races_touched


def ingest_sed(session: Session, df: pd.DataFrame, held_on: date) -> int:
    """Backfill race metadata from SED (race name / grade / surface / etc.).

    SED is post-race data. We only touch fields that are ``NULL`` in the
    existing race row to avoid clobbering BAC-sourced metadata.
    """
    if df.empty:
        return 0

    df = df.copy()
    df["race_key"] = df.apply(lambda r: build_race_key(r.to_dict()), axis=1)
    now = datetime.utcnow()
    touched = 0

    for race_key, group in df.groupby("race_key"):
        race = session.scalar(select(Race).where(Race.race_key == race_key))
        if race is None:
            # No KYI row yet — skip; we don't want a SED-only ghost race here.
            continue

        first = group.iloc[0]
        # SED's race-level metadata (always overwrite — SED is post-race truth).
        race.weather = _to_str(first.get("天候コード")) or race.weather
        race.distance = _to_int(first.get("距離")) or race.distance
        race.name = _to_str(first.get("レース名")) or race.name
        race.grade = _to_str(first.get("グレード")) or race.grade
        race.surface = _to_str(first.get("芝ダ障害コード")) or race.surface

        # 馬場状態 = 2 chars: [0]=芝 [1]=ダ (each 1:良 2:稍 3:重 4:不)
        ba = _to_str(first.get("馬場状態"))
        if ba and len(ba) >= 2 and ba.isdigit():
            race.condition = ba[1] if race.surface == "2" else ba[0]
        elif ba and ba.isdigit():
            race.condition = ba

        pt = _to_str(first.get("発走時間"))
        if pt and len(pt) == 4 and pt.isdigit():
            race.post_time = f"{pt[:2]}:{pt[2:]}"

        race.source = _merge_source(race.source, "SED")
        race.ingested_at = now
        touched += 1

    return touched


def ingest_bac(session: Session, df: pd.DataFrame, held_on: date) -> int:
    """Upsert BAC race-program data — race name / grade / distance / post time.

    BAC is the *pre-race* metadata source. Unlike SED, this is available at
    prediction time, so the API can show full race info on race day.

    Race rows are created here if they don't exist yet (BAC may arrive before
    KYI in some workflows). KYI/SED later fill in horse data.
    """
    if df.empty:
        return 0

    df = df.copy()
    df["race_key"] = df.apply(lambda r: build_race_key(r.to_dict()), axis=1)

    # Drop malformed race_keys (e.g. from a prior run with wrong record length).
    # Valid keys: venue 01-10, race_no 01-12.
    def _valid(k: str) -> bool:
        if not isinstance(k, str) or len(k) != 8 or not k.isdigit():
            return False
        venue = int(k[:2])
        race_no = int(k[6:8])
        return 1 <= venue <= 10 and 1 <= race_no <= 12

    df = df[df["race_key"].map(_valid)].copy()
    if df.empty:
        return 0

    now = datetime.utcnow()
    touched = 0

    for race_key, group in df.groupby("race_key"):
        first = group.iloc[0]
        race = session.scalar(select(Race).where(Race.race_key == race_key))
        if race is None:
            venue_code = f"{_to_int(first.get('場コード')) or 0:02d}"
            race = Race(
                race_key=str(race_key),
                held_on=held_on,
                venue_code=venue_code,
                venue=VENUE_NAMES.get(venue_code, venue_code),
                race_no=_to_int(first.get("R")) or 0,
                source="BAC",
                ingested_at=now,
            )
            session.add(race)
            session.flush()

        race.distance = _to_int(first.get("距離")) or race.distance
        race.surface = _to_str(first.get("芝ダ障害コード")) or race.surface
        race.grade = _to_str(first.get("グレード")) or race.grade

        name = _to_str(first.get("レース名"))
        if name:
            race.name = name
        elif not race.name:
            race.name = _to_str(first.get("レース名略称"))

        head = _to_int(first.get("頭数"))
        if head:
            race.head_count = head

        pt = _to_str(first.get("発走時間"))
        if pt and len(pt) == 4 and pt.isdigit():
            race.post_time = f"{pt[:2]}:{pt[2:]}"

        race.source = _merge_source(race.source, "BAC")
        race.ingested_at = now
        touched += 1

    return touched


def ingest_hjc(session: Session, df: pd.DataFrame, held_on: date) -> int:
    """Upsert HJC DataFrame into hjc_payout (raw JSON)."""
    if df.empty:
        return 0

    df = df.copy()
    df["race_key"] = df.apply(lambda r: build_race_key(r.to_dict()), axis=1)
    now = datetime.utcnow()
    touched = 0

    for race_key, group in df.groupby("race_key"):
        race = session.scalar(select(Race).where(Race.race_key == race_key))
        if race is None:
            # Defer: HJC without prior KYI — skip silently
            continue

        # Convert pandas Timestamp/NaN-safe
        raw_dict: dict = {}
        for col, val in group.iloc[0].items():
            if col == "race_key":
                continue
            if val is None:
                raw_dict[col] = None
            elif isinstance(val, float) and math.isnan(val):
                raw_dict[col] = None
            elif isinstance(val, (int, float, str, bool)):
                raw_dict[col] = val
            else:
                raw_dict[col] = str(val)

        payout = session.scalar(
            select(HjcPayout).where(HjcPayout.race_id == race.id)
        )
        if payout is None:
            session.add(HjcPayout(race_id=race.id, raw=raw_dict, ingested_at=now))
        else:
            payout.raw = raw_dict
            payout.ingested_at = now
        touched += 1

    return touched
