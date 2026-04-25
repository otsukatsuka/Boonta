"""Tests for 展開予想 formatter."""
import pandas as pd

from src.predict.tenkai import format_tenkai


def _make_race_df() -> pd.DataFrame:
    """Create sample prediction features DataFrame."""
    return pd.DataFrame({
        "race_key": ["06262a11"] * 4,
        "horse_number": [3, 7, 12, 5],
        "horse_name": ["ドウデュース", "リバティアイランド", "タスティエーラ", "テスト馬"],
        "running_style": [1, 2, 3, 4],
        "pace_forecast": ["M", "M", "M", "M"],
        "mid_position": [1, 3, 8, 10],
        "mid_gap": [0, 2, 5, 7],
        "mid_position_io": [2, 3, 4, 3],
        "late3f_position": [2, 3, 5, 8],
        "late3f_gap": [1, 2, 4, 6],
        "late3f_io": [2, 3, 4, 3],
        "goal_position": [1, 2, 3, 8],
        "goal_gap": [0, 1, 2, 6],
        "goal_io": [2, 3, 4, 3],
        "tenkai_symbol": ["A", "B", "C", "D"],
        "idm": [52.3, 48.5, 55.0, 40.0],
        "odds": [5.2, 8.0, 3.5, 50.0],
        "gate_miss_rate": [3.5, 5.0, 2.0, 12.5],
        "start_index": [5.2, 4.8, 6.0, 3.0],
        "upset_index": [45, 60, 30, 82],
    })


class TestFormatTenkai:
    def test_basic_output(self):
        df = _make_race_df()
        output = format_tenkai(df)

        assert "ペース予想" in output
        assert "位置取り予想" in output
        assert "=" * 50 in output

    def test_pace_forecast(self):
        df = _make_race_df()
        output = format_tenkai(df)

        assert "ミドル (M)" in output

    def test_front_runners(self):
        df = _make_race_df()
        output = format_tenkai(df)

        assert "逃げ馬" in output
        assert "3番" in output

    def test_position_table(self):
        df = _make_race_df()
        output = format_tenkai(df)

        assert "ドウデュース" in output
        assert "リバティアイランド" in output

    def test_with_predictions(self):
        df = _make_race_df()
        predictions = [0.78, 0.65, 0.58, 0.25]
        output = format_tenkai(df, predictions)

        assert "ML予測" in output
        assert "78.0%" in output

    def test_without_predictions(self):
        df = _make_race_df()
        output = format_tenkai(df)

        assert "ML予測" not in output

    def test_advantages(self):
        df = _make_race_df()
        output = format_tenkai(df)

        # Horse 3: goal_position=1, goal_io=2 → favorable
        assert "有利" in output

    def test_disadvantages(self):
        df = _make_race_df()
        output = format_tenkai(df)

        # Horse 5: gate_miss_rate=12.5 → disadvantage
        assert "不利" in output
        assert "12.5%" in output

    def test_upset_horses(self):
        df = _make_race_df()
        output = format_tenkai(df)

        # Horse 5: upset_index=82 >= 70 → upset alert
        assert "穴馬注意" in output
        assert "82" in output

    def test_no_upset_when_below_threshold(self):
        df = _make_race_df()
        df["upset_index"] = [30, 40, 50, 60]  # all below 70
        output = format_tenkai(df)

        assert "穴馬注意" not in output

    def test_bets_section_with_predictions(self):
        df = _make_race_df()
        df["fukusho_odds"] = [1.5, 2.0, 1.4, 8.0]
        predictions = [0.78, 0.65, 0.58, 0.25]
        output = format_tenkai(df, predictions)

        assert "期待値ランキング" in output
        assert "買い目" in output

    def test_no_bets_when_disabled(self):
        df = _make_race_df()
        predictions = [0.78, 0.65, 0.58, 0.25]
        output = format_tenkai(df, predictions, show_bets=False)

        assert "期待値ランキング" not in output
        assert "買い目" not in output

    def test_nagashi_section_with_axis(self):
        df = _make_race_df()
        # Force ev_fuku for horse 3 to clear threshold:
        # ev_fuku = prob * fukusho_odds → 0.78 * 1.5 = 1.17 > 1.0
        df["fukusho_odds"] = [1.5, 2.0, 1.4, 8.0]
        predictions = [0.78, 0.65, 0.58, 0.25]
        output = format_tenkai(df, predictions, ev_threshold=1.0)

        assert "3連複軸1頭流し" in output
        assert "見送り" not in output

    def test_nagashi_skipped_when_no_axis(self):
        df = _make_race_df()
        # All ev_fuku << 1.0
        df["fukusho_odds"] = [1.0, 1.0, 1.0, 1.0]
        predictions = [0.05, 0.05, 0.05, 0.05]
        output = format_tenkai(df, predictions, ev_threshold=1.0)

        assert "3連複軸1頭流し" in output
        assert "見送り" in output
