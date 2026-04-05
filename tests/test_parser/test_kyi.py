"""Tests for KYI field definitions with spec-compliant binary fixtures."""
from src.parser.engine import parse_record
from src.parser.kyi import KYI_FIELDS, RECORD_LENGTH


def _make_full_kyi_record(**overrides: tuple[int, str]) -> bytes:
    """Build a full 1024-byte KYI record with specific field values.

    Args:
        overrides: dict of {field_name: (offset_1based, value_str)} to place.
    """
    data = bytearray(1022)
    for i in range(1022):
        data[i] = 0x20  # fill with spaces (1022 data bytes + 2 CRLF = 1024)

    # Default race key + horse info
    defaults = {
        "場コード": (1, "06"),
        "年": (3, "26"),
        "回": (5, "2"),
        "日": (6, "a"),
        "R": (7, "11"),
        "馬番": (9, "03"),
        "血統登録番号": (11, "20190001"),
        "馬名": (19, "テスト馬名"),
        "IDM": (55, " 52.3"),
        "騎手指数": (60, " 48.5"),
        "情報指数": (65, " 45.0"),
        "総合指数": (85, " 60.1"),
        "脚質": (90, "1"),
        "距離適性": (91, "3"),
        "基準オッズ": (96, "  5.2"),
        "基準人気順位": (101, " 2"),
        "調教指数": (145, " 55.0"),
        "厩舎指数": (150, " 47.3"),
        "重適正コード": (166, "2"),
        "負担重量": (184, "550"),
        "枠番": (324, "3"),
        "テン指数": (359, " 48.5"),
        "ペース指数": (364, " 50.2"),
        "上がり指数": (369, " 53.1"),
        "位置指数": (374, " 46.8"),
        "ペース予想": (379, "M"),
        "道中順位": (380, " 3"),
        "道中差": (382, " 2"),
        "道中内外": (384, "3"),
        "後3F順位": (385, " 2"),
        "後3F差": (387, " 1"),
        "後3F内外": (389, "2"),
        "ゴール順位": (390, " 1"),
        "ゴール差": (392, " 0"),
        "ゴール内外": (394, "2"),
        "展開記号": (395, "A"),
        "取消フラグ": (403, "0"),
        "性別コード": (404, "1"),
        "馬スタート指数": (520, " 5.2"),
        "馬出遅率": (524, " 3.5"),
        "万券指数": (535, " 45"),
    }
    defaults.update(overrides)

    for _name, (offset, value) in defaults.items():
        encoded = value.encode("cp932")
        start = offset - 1
        data[start: start + len(encoded)] = encoded

    return bytes(data)


class TestKYIFields:
    def test_field_count(self):
        """KYI should have many fields defined."""
        assert len(KYI_FIELDS) > 80

    def test_record_length(self):
        assert RECORD_LENGTH == 1024

    def test_race_key(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["場コード"] == 6
        assert record["年"] == 26
        assert record["回"] == 2
        assert record["日"] == 10  # hex 'a' = 10
        assert record["R"] == 11

    def test_horse_info(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["馬番"] == 3
        assert record["血統登録番号"] == "20190001"
        assert record["馬名"] == "テスト馬名"

    def test_indices(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["IDM"] == 52.3
        assert record["騎手指数"] == 48.5
        assert record["情報指数"] == 45.0
        assert record["総合指数"] == 60.1
        assert record["調教指数"] == 55.0
        assert record["厩舎指数"] == 47.3

    def test_attributes(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["脚質"] == 1
        assert record["距離適性"] == 3
        assert record["重適正コード"] == 2

    def test_odds(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["基準オッズ"] == 5.2
        assert record["基準人気順位"] == 2

    def test_tenkai_data(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["テン指数"] == 48.5
        assert record["ペース指数"] == 50.2
        assert record["上がり指数"] == 53.1
        assert record["位置指数"] == 46.8
        assert record["ペース予想"] == "M"
        assert record["道中順位"] == 3
        assert record["道中差"] == 2
        assert record["道中内外"] == 3
        assert record["後3F順位"] == 2
        assert record["後3F差"] == 1
        assert record["後3F内外"] == 2
        assert record["ゴール順位"] == 1
        assert record["ゴール差"] == 0
        assert record["ゴール内外"] == 2
        assert record["展開記号"] == "A"

    def test_risk_data(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["馬スタート指数"] == 5.2
        assert record["馬出遅率"] == 3.5
        assert record["万券指数"] == 45

    def test_cancel_flag(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["取消フラグ"] == 0

    def test_sex_code(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["性別コード"] == 1  # 牡

    def test_weight(self):
        record = parse_record(_make_full_kyi_record(), KYI_FIELDS)
        assert record["負担重量"] == 550  # 55.0kg in 0.1kg units
        assert record["枠番"] == 3
