"""Tests for HJC field definitions with spec-compliant binary fixtures."""
from src.parser.engine import parse_record
from src.parser.hjc import HJC_FIELDS, RECORD_LENGTH


def _make_hjc_record() -> bytes:
    """Build a 444-byte HJC record with sample payoff data."""
    data = bytearray(442)
    for i in range(442):
        data[i] = 0x20  # 442 data bytes + 2 CRLF = 444

    def put(offset_1based: int, value: str):
        encoded = value.encode("cp932")
        start = offset_1based - 1
        data[start: start + len(encoded)] = encoded

    # レースキー
    put(1, "06")    # 場コード
    put(3, "26")    # 年
    put(5, "2")     # 回
    put(6, "a")     # 日
    put(7, "11")    # R

    # 単勝払戻 (3回, offset=9, 各9バイト)
    put(9,  "03")        # 単勝馬番_1
    put(11, "   1250")   # 単勝払戻_1
    put(18, "00")        # 単勝馬番_2 (empty)
    put(20, "      0")   # 単勝払戻_2

    # 複勝払戻 (5回, offset=36, 各9バイト)
    put(36, "03")        # 複勝馬番_1
    put(38, "    350")   # 複勝払戻_1
    put(45, "07")        # 複勝馬番_2
    put(47, "    420")   # 複勝払戻_2
    put(54, "12")        # 複勝馬番_3
    put(56, "    680")   # 複勝払戻_3

    # 馬連払戻 (3回, offset=108, 各12バイト)
    put(108, "0307")      # 馬連組合せ_1
    put(112, "    3250")  # 馬連払戻_1

    # 三連複払戻 (3回, offset=300, 各14バイト)
    put(300, "030712")    # 三連複組合せ_1
    put(306, "   15820")  # 三連複払戻_1

    # 三連単払戻 (6回, offset=342, 各15バイト)
    put(342, "030712")    # 三連単組合せ_1
    put(348, "    85430")  # 三連単払戻_1

    return bytes(data)


class TestHJCFields:
    def test_field_count(self):
        """HJC has many flattened fields for all bet types."""
        assert len(HJC_FIELDS) > 60

    def test_record_length(self):
        assert RECORD_LENGTH == 444

    def test_race_key(self):
        record = parse_record(_make_hjc_record(), HJC_FIELDS)
        assert record["場コード"] == 6
        assert record["年"] == 26
        assert record["R"] == 11

    def test_win_payoff(self):
        record = parse_record(_make_hjc_record(), HJC_FIELDS)
        assert record["単勝馬番_1"] == 3
        assert record["単勝払戻_1"] == 1250
        assert record["単勝馬番_2"] == 0
        assert record["単勝払戻_2"] == 0

    def test_place_payoff(self):
        record = parse_record(_make_hjc_record(), HJC_FIELDS)
        assert record["複勝馬番_1"] == 3
        assert record["複勝払戻_1"] == 350
        assert record["複勝馬番_2"] == 7
        assert record["複勝払戻_2"] == 420
        assert record["複勝馬番_3"] == 12
        assert record["複勝払戻_3"] == 680

    def test_quinella_payoff(self):
        record = parse_record(_make_hjc_record(), HJC_FIELDS)
        assert record["馬連組合せ_1"] == "0307"
        assert record["馬連払戻_1"] == 3250

    def test_trifecta_payoff(self):
        record = parse_record(_make_hjc_record(), HJC_FIELDS)
        assert record["三連複組合せ_1"] == "030712"
        assert record["三連複払戻_1"] == 15820

    def test_trio_payoff(self):
        record = parse_record(_make_hjc_record(), HJC_FIELDS)
        assert record["三連単組合せ_1"] == "030712"
        assert record["三連単払戻_1"] == 85430

    def test_empty_slots(self):
        """Empty payoff slots should return None or 0."""
        record = parse_record(_make_hjc_record(), HJC_FIELDS)
        # 単勝馬番_3 is empty (spaces)
        assert record["単勝馬番_3"] is None
