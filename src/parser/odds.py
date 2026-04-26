"""Parsers for JRDB pre-race combination-odds files.

These files store one record per race with N repeating odds values:

* **OW** (基準オッズワイドデータ) — record 780 B, 153 wide combos × 5 B (ZZ9.9)
  combo order: 1-2, 1-3, ..., 1-18, 2-3, ..., 17-18 (sorted pairs)
* **OU** (基準オッズ馬単データ) — record 1856 B, 306 umatan permutations × 6 B
  combo order: 1-2, 1-3, ..., 1-18, 2-1, 2-3, ..., 18-17 (ordered pairs i≠j)
* **OT** (基準オッズ３連複データ) — record 4912 B, 816 sanrenpuku combos × 6 B
  combo order: 1-2-3, 1-2-4, ..., 1-2-18, 1-3-4, ..., 16-17-18 (sorted triplets)

A cancelled combo is encoded as 9999.9 (after numeric stripping). All combos
are stored even when the actual race has < 18 horses; downstream code should
filter against the race's actual entries.
"""
from __future__ import annotations

from itertools import combinations, permutations
from pathlib import Path

import pandas as pd

from src.parser.engine import build_race_key

# Constants
MAX_HORSES = 18
CANCELLED_ODDS = 9999.9

OW_RECORD_LENGTH = 780
OU_RECORD_LENGTH = 1856
OT_RECORD_LENGTH = 4912


def _decode_field(raw: bytes) -> str:
    return raw.decode("cp932", errors="replace").strip()


def _parse_decimal(text: str) -> float | None:
    """Parse ZZ9.9 / ZZZ9.9 string into float; empty → None."""
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_race_header(line: bytes) -> dict[str, object]:
    """Parse the race-key + 登録頭数 prefix shared by OW/OU/OT."""
    record = {
        "場コード": int(_decode_field(line[0:2])) if line[0:2].strip() else None,
        "年": int(_decode_field(line[2:4])) if line[2:4].strip() else None,
        "回": int(_decode_field(line[4:5])) if line[4:5].strip() else None,
        "日": int(_decode_field(line[5:6]), 16) if line[5:6].strip() else None,
        "R": int(_decode_field(line[6:8])) if line[6:8].strip() else None,
    }
    head_text = _decode_field(line[8:10])
    record["登録頭数"] = int(head_text) if head_text else None
    record["race_key"] = build_race_key(record)
    return record


def _wide_combo_keys() -> list[str]:
    """Combo keys in JRDB OW order: 01-02, 01-03, ..., 17-18."""
    return [f"{a:02d}-{b:02d}" for a, b in combinations(range(1, MAX_HORSES + 1), 2)]


def _umatan_combo_keys() -> list[str]:
    """Combo keys in JRDB OU order: 01-02, 01-03, ..., 18-17."""
    keys: list[str] = []
    for a in range(1, MAX_HORSES + 1):
        for b in range(1, MAX_HORSES + 1):
            if a == b:
                continue
            keys.append(f"{a:02d}-{b:02d}")
    return keys


def _sanrenpuku_combo_keys() -> list[str]:
    """Combo keys in JRDB OT order: 01-02-03, ..., 16-17-18."""
    return [
        f"{a:02d}-{b:02d}-{c:02d}"
        for a, b, c in combinations(range(1, MAX_HORSES + 1), 3)
    ]


# Sanrentan order — JRDB does not provide an OT3 file in this dataset, but
# leaving this here for future use. Permutations of 3 distinct horses.
def _sanrentan_combo_keys() -> list[str]:
    return [
        f"{a:02d}-{b:02d}-{c:02d}"
        for a, b, c in permutations(range(1, MAX_HORSES + 1), 3)
    ]


def _parse_odds_record(
    line: bytes,
    odds_offset: int,
    occ: int,
    field_size: int,
    combo_keys: list[str],
) -> dict[str, float | None]:
    """Slice ``occ`` odds out of ``line`` starting at byte ``odds_offset``.

    Returns a dict mapping combo_key → odds (None for empty / cancelled).
    Cancellation marker depends on field width:
      * 5-byte (ZZ9.9): max representable = 999.9 — treat ≥ 999.85 as cancelled.
      * 6-byte (ZZZ9.9): max representable = 9999.9 — treat ≥ 9999.85 as cancelled.
    """
    cancelled_threshold = 999.85 if field_size == 5 else 9999.85
    out: dict[str, float | None] = {}
    for i, key in enumerate(combo_keys):
        start = (odds_offset - 1) + i * field_size
        end = start + field_size
        text = _decode_field(line[start:end])
        val = _parse_decimal(text)
        if val is None or val == 0.0 or val >= cancelled_threshold:
            out[key] = None
        else:
            out[key] = val
    return out


def _parse_file(
    path: Path,
    record_length: int,
    bet_type: str,
    odds_offset: int,
    occ: int,
    field_size: int,
    combo_keys: list[str],
) -> pd.DataFrame:
    with open(path, "rb") as fh:
        raw = fh.read()

    records = []
    for i in range(0, len(raw), record_length):
        line = raw[i: i + record_length]
        if len(line) < record_length - 2:
            continue
        header = _parse_race_header(line)
        odds_dict = _parse_odds_record(line, odds_offset, occ, field_size, combo_keys)
        records.append({
            "race_key": header["race_key"],
            "head_count": header["登録頭数"],
            "bet_type": bet_type,
            "odds": odds_dict,
        })
    return pd.DataFrame(records)


def parse_ow_file(path: Path) -> pd.DataFrame:
    """Parse OW (基準オッズワイドデータ). Returns DataFrame with race_key,
    head_count, bet_type='wide', odds={combo_key: odds | None}."""
    return _parse_file(
        path,
        OW_RECORD_LENGTH,
        "wide",
        odds_offset=11,
        occ=153,
        field_size=5,
        combo_keys=_wide_combo_keys(),
    )


def parse_ou_file(path: Path) -> pd.DataFrame:
    """Parse OU (基準オッズ馬単データ). Returns DataFrame with race_key,
    head_count, bet_type='umatan', odds={combo_key: odds | None}."""
    return _parse_file(
        path,
        OU_RECORD_LENGTH,
        "umatan",
        odds_offset=11,
        occ=306,
        field_size=6,
        combo_keys=_umatan_combo_keys(),
    )


def parse_ot_file(path: Path) -> pd.DataFrame:
    """Parse OT (基準オッズ三連複データ). Returns DataFrame with race_key,
    head_count, bet_type='sanrenpuku', odds={combo_key: odds | None}."""
    return _parse_file(
        path,
        OT_RECORD_LENGTH,
        "sanrenpuku",
        odds_offset=11,
        occ=816,
        field_size=6,
        combo_keys=_sanrenpuku_combo_keys(),
    )
