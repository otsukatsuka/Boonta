"""JRDB code → human label mappings (used at API layer, not stored in DB).

Codes are kept as-is in DB; converted only when serializing to the wire so the
mapping can be revised without touching the database.
"""
from __future__ import annotations

SURFACE: dict[str, str] = {
    "1": "芝",
    "2": "ダ",
    "3": "障",
}

CONDITION: dict[str, str] = {
    "1": "良",
    "2": "稍",
    "3": "重",
    "4": "不",
}

WEATHER: dict[str, str] = {
    "1": "晴",
    "2": "曇",
    "3": "雨",
    "4": "小雨",
    "5": "雪",
    "6": "小雪",
}

# SED グレード: 1=G1 / 2=G2 / 3=G3 / 4=重賞 / 5=特別 / 6=L
GRADE: dict[str, str] = {
    "1": "G1",
    "2": "G2",
    "3": "G3",
    "4": "重賞",
    "5": "特別",
    "6": "L",
}


def label(table: dict[str, str], code: str | None) -> str | None:
    if code is None:
        return None
    s = str(code).strip()
    if not s:
        return None
    # Normalize "5.0" → "5" (BAC's numeric grade is parsed as float via spec).
    try:
        s = str(int(float(s)))
    except (TypeError, ValueError):
        pass
    return table.get(s, s)
