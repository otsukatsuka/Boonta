"""Tests for parse_record, parse_file, and build_race_key."""
from pathlib import Path
import tempfile

import pandas as pd

from src.parser.engine import build_race_key, parse_file, parse_record
from src.parser.spec import FieldSpec


def _make_kyi_record_bytes(
    basho: str = "06",
    nen: str = "26",
    kai: str = "2",
    nichi: str = "a",
    r: str = "11",
    umaban: str = "03",
    touroku: str = "12345678",
    bamei: str = "ドウデュース",
    idm: str = " 52.3",
    total_length: int = 1024,
) -> bytes:
    """Build a minimal KYI record with known fields for testing.

    Fills remaining bytes with spaces to match record_length.
    """
    # Build the record in CP932
    data = bytearray(total_length)
    # Fill with spaces (0x20)
    for i in range(total_length):
        data[i] = 0x20

    # Place fields at 1-based offsets (convert to 0-based)
    def put(offset_1based: int, value: str, encoding: str = "cp932"):
        encoded = value.encode(encoding)
        start = offset_1based - 1
        data[start: start + len(encoded)] = encoded

    put(1, basho)       # 場コード
    put(3, nen)         # 年
    put(5, kai)         # 回
    put(6, nichi)       # 日 (hex)
    put(7, r)           # R
    put(9, umaban)      # 馬番
    put(11, touroku)    # 血統登録番号
    put(19, bamei)      # 馬名
    put(55, idm)        # IDM

    return bytes(data)


# Minimal fields for testing
MINI_FIELDS = [
    FieldSpec("場コード",  1, 2, "numeric"),
    FieldSpec("年",        3, 2, "numeric"),
    FieldSpec("回",        5, 1, "numeric"),
    FieldSpec("日",        6, 1, "hex"),
    FieldSpec("R",         7, 2, "numeric"),
    FieldSpec("馬番",      9, 2, "numeric"),
    FieldSpec("血統登録番号", 11, 8, "text"),
    FieldSpec("馬名",     19, 36, "text"),
    FieldSpec("IDM",      55,  5, "decimal", scale=1),
]


class TestParseRecord:
    def test_basic_fields(self):
        line = _make_kyi_record_bytes()
        record = parse_record(line, MINI_FIELDS)

        assert record["場コード"] == 6
        assert record["年"] == 26
        assert record["回"] == 2
        assert record["日"] == 10  # 'a' hex = 10
        assert record["R"] == 11
        assert record["馬番"] == 3
        assert record["血統登録番号"] == "12345678"
        assert record["馬名"] == "ドウデュース"
        assert record["IDM"] == 52.3

    def test_empty_fields(self):
        """All-space record should produce None for numeric/decimal fields."""
        line = b" " * 1024
        record = parse_record(line, MINI_FIELDS)
        assert record["場コード"] is None
        assert record["IDM"] is None
        assert record["馬名"] is None


class TestParseFile:
    def test_single_record(self):
        record_data = _make_kyi_record_bytes()
        file_data = record_data + b"\r\n"  # CRLF

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(file_data)
            f.flush()
            path = Path(f.name)

        df = parse_file(path, MINI_FIELDS, 1026)
        assert len(df) == 1
        assert df.iloc[0]["馬番"] == 3
        assert df.iloc[0]["馬名"] == "ドウデュース"
        path.unlink()

    def test_multiple_records(self):
        rec1 = _make_kyi_record_bytes(umaban="01", bamei="テスト馬１")
        rec2 = _make_kyi_record_bytes(umaban="02", bamei="テスト馬２")
        file_data = rec1 + b"\r\n" + rec2 + b"\r\n"

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(file_data)
            f.flush()
            path = Path(f.name)

        df = parse_file(path, MINI_FIELDS, 1026)
        assert len(df) == 2
        assert df.iloc[0]["馬番"] == 1
        assert df.iloc[1]["馬番"] == 2
        path.unlink()

    def test_returns_dataframe(self):
        rec = _make_kyi_record_bytes() + b"\r\n"
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(rec)
            path = Path(f.name)

        result = parse_file(path, MINI_FIELDS, 1026)
        assert isinstance(result, pd.DataFrame)
        path.unlink()


class TestBuildRaceKey:
    def test_normal(self):
        record = {"場コード": 6, "年": 26, "回": 2, "日": 10, "R": 11}
        assert build_race_key(record) == "06262a11"

    def test_hex_day(self):
        record = {"場コード": 5, "年": 25, "回": 1, "日": 15, "R": 1}
        assert build_race_key(record) == "05251f01"  # 回=1, 日=f(15)

    def test_numeric_day(self):
        record = {"場コード": 1, "年": 20, "回": 3, "日": 5, "R": 8}
        assert build_race_key(record) == "01203508"
