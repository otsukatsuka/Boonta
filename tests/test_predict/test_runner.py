"""Tests for prediction runner."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.predict.runner import run_prediction


def _make_kyi_file(n_horses: int = 3) -> Path:
    """Create a minimal KYI file for testing."""
    records = []
    for i in range(1, n_horses + 1):
        data = bytearray(1022)
        for j in range(1022):
            data[j] = 0x20

        def put(offset, value, encoding="cp932"):
            encoded = value.encode(encoding)
            data[offset - 1: offset - 1 + len(encoded)] = encoded

        put(1, "06")       # 場コード
        put(3, "26")       # 年
        put(5, "2")        # 回
        put(6, "a")        # 日
        put(7, "11")       # R
        put(9, f"{i:02d}")  # 馬番
        put(19, f"テスト馬{i}")
        put(55, " 50.0")   # IDM
        put(60, " 50.0")   # 騎手指数
        put(65, " 50.0")   # 情報指数
        put(85, " 50.0")   # 総合指数
        put(90, "1")       # 脚質
        put(96, " 10.0")   # 基準オッズ
        put(101, f" {i}")  # 基準人気順位
        put(184, "550")    # 負担重量
        put(324, f"{i}")   # 枠番
        put(359, " 50.0")  # テン指数
        put(364, " 50.0")  # ペース指数
        put(369, " 50.0")  # 上がり指数
        put(374, " 50.0")  # 位置指数
        put(379, "M")      # ペース予想
        put(380, f" {i}")  # 道中順位
        put(385, f" {i}")  # 後3F順位
        put(390, f" {i}")  # ゴール順位
        put(520, " 5.0")   # 馬スタート指数
        put(524, " 3.0")   # 馬出遅率
        put(535, " 50")    # 万券指数

        records.append(bytes(data) + b"\r\n")

    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    tmp.write(b"".join(records))
    tmp.close()
    return Path(tmp.name)


class TestRunPrediction:
    def test_without_client(self):
        """Run prediction without Modal client (展開予想 only)."""
        path = _make_kyi_file(3)
        output = run_prediction(path, client=None)

        assert "ペース予想" in output
        assert "位置取り予想" in output
        assert "ML予測" not in output
        path.unlink()

    def test_with_mock_client(self):
        """Run prediction with mocked Modal client."""
        path = _make_kyi_file(3)

        mock_client = MagicMock()
        mock_client.predict.return_value = {
            "success": True,
            "predictions": [0.8, 0.6, 0.4],
        }

        output = run_prediction(path, client=mock_client)

        assert "ML予測" in output
        assert "80.0%" in output
        path.unlink()

    def test_race_filter(self):
        """Filter by race number."""
        path = _make_kyi_file(3)
        output = run_prediction(path, client=None, race_number=11)

        assert "ペース予想" in output
        path.unlink()

    def test_race_filter_not_found(self):
        """Race number not in file."""
        path = _make_kyi_file(3)
        output = run_prediction(path, client=None, race_number=99)

        assert "not found" in output
        path.unlink()

    def test_client_error_handled(self):
        """Modal client error doesn't crash."""
        path = _make_kyi_file(3)

        mock_client = MagicMock()
        mock_client.predict.side_effect = Exception("Connection failed")

        output = run_prediction(path, client=mock_client)

        # Should still produce output (without ML predictions)
        assert "ペース予想" in output
        assert "ML予測" not in output
        path.unlink()
