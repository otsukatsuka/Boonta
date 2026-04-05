"""Tests for SED field definitions with spec-compliant binary fixtures."""
from src.parser.engine import parse_record
from src.parser.sed import SED_FIELDS, RECORD_LENGTH


def _make_sed_record(**overrides: tuple[int, str]) -> bytes:
    """Build a 376-byte SED record."""
    data = bytearray(376)
    for i in range(376):
        data[i] = 0x20

    defaults = {
        "場コード": (1, "06"),
        "年": (3, "26"),
        "回": (5, "2"),
        "日": (6, "a"),
        "R": (7, "11"),
        "馬番": (9, "03"),
        "血統登録番号": (11, "20190001"),
        "年月日": (19, "20260405"),
        "馬名": (27, "テスト馬"),
        "距離": (63, "2000"),
        "芝ダ障害コード": (67, "1"),
        "馬場状態": (70, "01"),
        "グレード": (80, "1"),
        "頭数": (131, "16"),
        "着順": (141, "01"),
        "異常区分": (143, "0"),
        "タイ��": (144, "2001"),  # 2:00.1
        "確定単勝オッズ": (175, "   5.2"),
        "テン指数": (224, " 48.5"),
        "上がり指数": (229, " 53.1"),
        "ペース指数": (234, " 50.2"),
        "レースペース": (222, "M"),
        "馬ペース": (223, "M"),
        "前3Fタイム": (259, "351"),  # 35.1秒
        "後3Fタイム": (262, "334"),  # 33.4秒
        "コーナー順位1": (309, "05"),
        "コーナー順位2": (311, "04"),
        "コーナー順位3": (313, "03"),
        "コーナー順位4": (315, "02"),
        "馬体重": (333, "480"),
        "馬体重増減": (336, "+04"),
        "レース脚質": (341, "2"),
        "4角コース取り": (370, "3"),
    }
    defaults.update(overrides)

    for _name, (offset, value) in defaults.items():
        encoded = value.encode("cp932")
        start = offset - 1
        data[start: start + len(encoded)] = encoded

    return bytes(data)


class TestSEDFields:
    def test_field_count(self):
        assert len(SED_FIELDS) > 50

    def test_record_length(self):
        assert RECORD_LENGTH == 378

    def test_race_key(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["場コード"] == 6
        assert record["年"] == 26
        assert record["R"] == 11

    def test_race_conditions(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["距離"] == 2000
        assert record["芝ダ障害コード"] == 1  # 芝
        assert record["グレード"] == 1  # G1
        assert record["頭数"] == 16

    def test_result(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["着順"] == 1
        assert record["異常区分"] == 0
        assert record["タイム"] == 2001

    def test_odds(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["確定単勝オッズ"] == 5.2

    def test_speed_indices(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["テン指数"] == 48.5
        assert record["上がり指数"] == 53.1
        assert record["ペース指数"] == 50.2

    def test_pace(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["レースペース"] == "M"
        assert record["馬ペース"] == "M"

    def test_timing(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["前3Fタイム"] == 351
        assert record["後3Fタイム"] == 334

    def test_corner_positions(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["コーナー順位1"] == 5
        assert record["コーナー順位2"] == 4
        assert record["コーナー順位3"] == 3
        assert record["コーナー順位4"] == 2

    def test_weight(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["馬体重"] == 480
        assert record["馬体重増減"] == "+04"

    def test_running_style(self):
        record = parse_record(_make_sed_record(), SED_FIELDS)
        assert record["レース脚質"] == "2"  # text type
        assert record["4角コース取り"] == 3
