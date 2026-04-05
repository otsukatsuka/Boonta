"""Tests for feature engineering pipeline."""
import numpy as np
import pandas as pd
import pytest

from src.features.columns import FEATURE_COLUMNS, LABEL_COLUMN
from src.features.derived import add_derived_features
from src.features.engineering import (
    build_prediction_features,
    build_training_features,
    preprocess,
)


def _make_kyi_df(n: int = 3) -> pd.DataFrame:
    """Create a sample KYI-like DataFrame."""
    return pd.DataFrame({
        "場コード": [6] * n,
        "年": [26] * n,
        "回": [2] * n,
        "日": [10] * n,
        "R": [11] * n,
        "馬番": list(range(1, n + 1)),
        "馬名": [f"馬{i}" for i in range(1, n + 1)],
        "IDM": [52.3, 48.5, 55.0][:n],
        "騎手指数": [48.5, 45.0, 50.0][:n],
        "情報指数": [45.0, 42.0, 48.0][:n],
        "総合指数": [60.1, 55.0, 62.0][:n],
        "調教指数": [55.0, 50.0, 58.0][:n],
        "厩舎指数": [47.3, 44.0, 49.0][:n],
        "脚質": [1, 2, 3][:n],
        "距離適性": [3, 2, 3][:n],
        "重適正コード": [2, 1, 2][:n],
        "基準オッズ": [5.2, 8.0, 3.5][:n],
        "基準人気順位": [2, 4, 1][:n],
        "負担重量": [550, 540, 560][:n],  # 0.1kg units
        "枠番": [3, 5, 1][:n],
        "テン指数": [48.5, 50.0, 46.0][:n],
        "ペース指数": [50.2, 48.0, 52.0][:n],
        "上がり指数": [53.1, 50.0, 55.0][:n],
        "位置指数": [46.8, 45.0, 48.0][:n],
        "ペース予想": ["M", "H", "S"][:n],
        "道中順位": [3, 1, 5][:n],
        "道中差": [2, 0, 4][:n],
        "道中内外": [3, 2, 4][:n],
        "後3F順位": [2, 3, 4][:n],
        "後3F差": [1, 2, 3][:n],
        "後3F内外": [2, 3, 4][:n],
        "ゴール順位": [1, 2, 6][:n],
        "ゴール差": [0, 1, 5][:n],
        "ゴール内外": [2, 3, 4][:n],
        "展開記号": ["A", "B", "C"][:n],
        "馬スタート指数": [5.2, 4.8, 6.0][:n],
        "馬出遅率": [3.5, 5.0, 2.0][:n],
        "万券指数": [45, 60, 30][:n],
    })


def _make_sed_df(n: int = 3) -> pd.DataFrame:
    """Create a sample SED-like DataFrame with matching race keys."""
    return pd.DataFrame({
        "場コード": [6] * n,
        "年": [26] * n,
        "回": [2] * n,
        "日": [10] * n,
        "R": [11] * n,
        "馬番": list(range(1, n + 1)),
        "着順": [1, 3, 8][:n],
        "異常区分": [0, 0, 0][:n],
    })


class TestBuildTrainingFeatures:
    def test_basic(self):
        kyi = _make_kyi_df()
        sed = _make_sed_df()
        result = build_training_features(kyi, sed)

        assert LABEL_COLUMN in result.columns
        assert len(result) == 3

    def test_is_place_label(self):
        kyi = _make_kyi_df()
        sed = _make_sed_df()
        result = build_training_features(kyi, sed)

        # 着順 1,3 → is_place=1; 着順 8 → is_place=0
        assert result[LABEL_COLUMN].tolist() == [1, 1, 0]

    def test_anomaly_filter(self):
        kyi = _make_kyi_df()
        sed = _make_sed_df()
        sed.loc[2, "異常区分"] = 1  # 取消

        result = build_training_features(kyi, sed)
        assert len(result) == 2  # horse 3 filtered out

    def test_feature_columns_present(self):
        kyi = _make_kyi_df()
        sed = _make_sed_df()
        result = build_training_features(kyi, sed)

        for col in ["idm", "jockey_index", "odds", "pace_forecast"]:
            assert col in result.columns

    def test_weight_converted(self):
        kyi = _make_kyi_df()
        sed = _make_sed_df()
        result = build_training_features(kyi, sed)

        assert result["weight_carried"].iloc[0] == 55.0  # 550 / 10

    def test_derived_features(self):
        kyi = _make_kyi_df()
        sed = _make_sed_df()
        result = build_training_features(kyi, sed)

        assert "speed_balance" in result.columns
        assert "position_delta" in result.columns
        assert "log_odds" in result.columns


class TestBuildPredictionFeatures:
    def test_basic(self):
        kyi = _make_kyi_df()
        result = build_prediction_features(kyi)

        assert LABEL_COLUMN not in result.columns
        assert len(result) == 3

    def test_has_metadata(self):
        kyi = _make_kyi_df()
        result = build_prediction_features(kyi)

        assert "race_key" in result.columns
        assert "horse_number" in result.columns
        assert "horse_name" in result.columns

    def test_has_features(self):
        kyi = _make_kyi_df()
        result = build_prediction_features(kyi)

        for col in ["idm", "odds", "pace_forecast", "speed_balance"]:
            assert col in result.columns


class TestPreprocess:
    def test_fills_missing_numerics(self):
        df = pd.DataFrame({"idm": [None, 52.3], "odds": [None, 5.0]})
        result = preprocess(df)

        assert result["idm"].iloc[0] == 50.0
        assert result["odds"].iloc[0] == 10.0

    def test_fills_missing_categoricals(self):
        df = pd.DataFrame({"pace_forecast": [None, "M"]})
        result = preprocess(df)

        assert result["pace_forecast"].iloc[0] == "Unknown"
        assert result["pace_forecast"].iloc[1] == "M"


class TestDerivedFeatures:
    def test_speed_balance(self):
        df = pd.DataFrame({"ten_index": [48.5], "agari_index": [53.1]})
        result = add_derived_features(df)
        assert abs(result["speed_balance"].iloc[0] - (-4.6)) < 0.01

    def test_position_delta(self):
        df = pd.DataFrame({"goal_position": [1], "mid_position": [3]})
        result = add_derived_features(df)
        assert result["position_delta"].iloc[0] == -2

    def test_io_shift(self):
        df = pd.DataFrame({"goal_io": [2], "mid_position_io": [4]})
        result = add_derived_features(df)
        assert result["io_shift"].iloc[0] == -2

    def test_log_odds(self):
        df = pd.DataFrame({"odds": [10.0]})
        result = add_derived_features(df)
        assert abs(result["log_odds"].iloc[0] - np.log(10.0)) < 0.01

    def test_risk_score(self):
        df = pd.DataFrame({"gate_miss_rate": [5.0], "start_index": [5.0]})
        result = add_derived_features(df)
        expected = 5.0 * (1 - 5.0 / 10)  # = 2.5
        assert abs(result["risk_score"].iloc[0] - expected) < 0.01

    def test_race_head_count_from_race_key(self):
        df = pd.DataFrame({
            "race_key": ["A", "A", "A", "B", "B"],
            "horse_number": [1, 2, 3, 1, 2],
        })
        result = add_derived_features(df)
        assert result["race_head_count"].iloc[0] == 3
        assert result["race_head_count"].iloc[3] == 2
