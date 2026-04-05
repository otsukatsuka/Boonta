"""Generic fixed-length record parser engine for JRDB files."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.parser.spec import FieldSpec, coerce


def parse_record(line: bytes, fields: list[FieldSpec]) -> dict[str, object]:
    """Parse a single fixed-length record into a dict.

    Args:
        line: Raw bytes for one record (may include CRLF).
        fields: Field specifications defining the record layout.

    Returns:
        Dict mapping field names to converted values.
    """
    record: dict[str, object] = {}
    for f in fields:
        start = f.offset - 1  # 1-based → 0-based
        end = start + f.length
        raw = line[start:end]
        text = raw.decode("cp932", errors="replace").strip()
        record[f.name] = coerce(text, f.field_type, f.scale, f.signed)
    return record


def parse_file(
    path: Path,
    fields: list[FieldSpec],
    record_length: int,
) -> pd.DataFrame:
    """Parse an entire JRDB fixed-length file into a DataFrame.

    Args:
        path: Path to the raw JRDB text file.
        fields: Field specifications for the record type.
        record_length: Total record length including CRLF (e.g. 1026 for KYI).

    Returns:
        DataFrame with one row per record and columns per field.
    """
    with open(path, "rb") as fh:
        raw = fh.read()

    records = []
    for i in range(0, len(raw), record_length):
        line = raw[i: i + record_length]
        # Allow records that are at least record_length - 2 (missing CRLF at EOF)
        if len(line) >= record_length - 2:
            records.append(parse_record(line, fields))

    return pd.DataFrame(records)


def build_race_key(record: dict[str, object]) -> str:
    """Build an 8-character race key from parsed record fields.

    Race key structure: 場コード(2) + 年(2) + 回(1) + 日(1,hex) + R(2)

    The 日 field is hex-encoded in the original data and stored as int after parsing.
    We convert it back to a single hex character for the key.
    """
    basho = int(record.get("場コード") or 0)
    nen = int(record.get("年") or 0)
    kai = int(record.get("回") or 0)
    nichi = record.get("日") or 0
    r = int(record.get("R") or 0)
    # 日 is already parsed as int from hex; convert back to hex char
    nichi_hex = format(int(nichi), "x")
    return f"{basho:02d}{nen:02d}{kai}{nichi_hex}{r:02d}"
