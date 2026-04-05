"""Tests for ROI evaluation with known predictions and HJC data."""
import pandas as pd
import pytest

from src.predict.roi import evaluate_roi


@pytest.fixture
def predictions_df():
    """Predictions for 2 races."""
    return pd.DataFrame({
        "race_key": ["R001"] * 4 + ["R002"] * 3,
        "horse_number": [3, 7, 12, 5, 1, 4, 8],
        "predict_prob": [0.78, 0.65, 0.58, 0.25, 0.72, 0.60, 0.40],
    })


@pytest.fixture
def hjc_df():
    """HJC payoff data for 2 races."""
    data = {
        "race_key": ["R001", "R002"],
        # 複勝 (place) payoffs
        "複勝馬番_1": [3, 1],
        "複勝払戻_1": [350, 250],
        "複勝馬番_2": [7, 6],
        "複勝払戻_2": [420, 300],
        "複勝馬番_3": [12, 8],
        "複勝払戻_3": [680, 450],
        "複勝馬番_4": [0, 0],
        "複勝払戻_4": [0, 0],
        "複勝馬番_5": [0, 0],
        "複勝払戻_5": [0, 0],
        # 馬連 (quinella) payoffs
        "馬連組合せ_1": ["0307", "0106"],
        "馬連払戻_1": [3250, 2800],
        "馬連組合せ_2": ["", ""],
        "馬連払戻_2": [0, 0],
        "馬連組合せ_3": ["", ""],
        "馬連払戻_3": [0, 0],
        # 三連複 (trifecta) payoffs
        "三連複組合せ_1": ["030712", "010608"],
        "三連複払戻_1": [15820, 8500],
        "三連複組合せ_2": ["", ""],
        "三連複払戻_2": [0, 0],
        "三連複組合せ_3": ["", ""],
        "三連複払戻_3": [0, 0],
    }
    return pd.DataFrame(data)


class TestEvaluateROI:
    def test_invalid_strategy(self, predictions_df, hjc_df):
        with pytest.raises(ValueError, match="Unknown strategy"):
            evaluate_roi(predictions_df, hjc_df, "invalid")


class TestFukushoStrategy:
    def test_basic(self, predictions_df, hjc_df):
        result = evaluate_roi(predictions_df, hjc_df, "fukusho_top3")
        assert result["strategy"] == "fukusho_top3"
        assert result["race_count"] == 2

    def test_bets_count(self, predictions_df, hjc_df):
        result = evaluate_roi(predictions_df, hjc_df, "fukusho_top3")
        # 2 races × 3 horses × 100 yen = 600 yen
        assert result["total_bets"] == 600

    def test_returns_race1(self, predictions_df, hjc_df):
        """Race 1: top 3 = [3, 7, 12], all are place winners."""
        result = evaluate_roi(predictions_df, hjc_df, "fukusho_top3")
        # Race 1: 3→350, 7→420, 12→680 = 1450
        # Race 2: top 3 = [1, 4, 8], 1→250, 8→450 = 700
        assert result["total_return"] == 1450 + 700

    def test_hit_count(self, predictions_df, hjc_df):
        result = evaluate_roi(predictions_df, hjc_df, "fukusho_top3")
        # Race 1: 3 hits, Race 2: 2 hits (horse 4 not in place)
        assert result["hit_count"] == 5

    def test_roi_calculation(self, predictions_df, hjc_df):
        result = evaluate_roi(predictions_df, hjc_df, "fukusho_top3")
        expected_roi = round((2150 / 600) * 100, 1)
        assert result["roi"] == expected_roi


class TestUmarenStrategy:
    def test_basic(self, predictions_df, hjc_df):
        result = evaluate_roi(predictions_df, hjc_df, "umaren_top2")
        assert result["strategy"] == "umaren_top2"
        assert result["race_count"] == 2

    def test_hit_race1(self, predictions_df, hjc_df):
        """Race 1: top 2 = [3, 7], quinella = 0307 → hit."""
        result = evaluate_roi(predictions_df, hjc_df, "umaren_top2")
        # Race 1: combo {3,7} matches "0307" → 3250
        # Race 2: combo {1,4} doesn't match "0106" → 0
        assert result["total_return"] == 3250
        assert result["hit_count"] == 1

    def test_bets(self, predictions_df, hjc_df):
        result = evaluate_roi(predictions_df, hjc_df, "umaren_top2")
        assert result["total_bets"] == 200  # 2 races × 100


class TestSanrenpukuStrategy:
    def test_basic(self, predictions_df, hjc_df):
        result = evaluate_roi(predictions_df, hjc_df, "sanrenpuku_top3")
        assert result["strategy"] == "sanrenpuku_top3"

    def test_hit_race1(self, predictions_df, hjc_df):
        """Race 1: top 3 = [3, 7, 12], trifecta = 030712 → hit."""
        result = evaluate_roi(predictions_df, hjc_df, "sanrenpuku_top3")
        # Race 1: {3,7,12} matches "030712" → 15820
        # Race 2: {1,4,8} doesn't match "010608" → 0
        assert result["total_return"] == 15820
        assert result["hit_count"] == 1

    def test_details(self, predictions_df, hjc_df):
        result = evaluate_roi(predictions_df, hjc_df, "sanrenpuku_top3")
        assert len(result["details"]) == 2
        assert result["details"][0]["hit"] is True
        assert result["details"][1]["hit"] is False


class TestEdgeCases:
    def test_no_matching_races(self):
        predictions = pd.DataFrame({
            "race_key": ["X001"],
            "horse_number": [1],
            "predict_prob": [0.5],
        })
        hjc = pd.DataFrame({
            "race_key": ["Y001"],
            "複勝馬番_1": [1], "複勝払戻_1": [200],
            "複勝馬番_2": [0], "複勝払戻_2": [0],
            "複勝馬番_3": [0], "複勝払戻_3": [0],
            "複勝馬番_4": [0], "複勝払戻_4": [0],
            "複勝馬番_5": [0], "複勝払戻_5": [0],
        })
        result = evaluate_roi(predictions, hjc, "fukusho_top3")
        assert result["race_count"] == 0
        assert result["total_bets"] == 0
        assert result["roi"] == 0.0

    def test_empty_predictions(self):
        predictions = pd.DataFrame(columns=["race_key", "horse_number", "predict_prob"])
        hjc = pd.DataFrame(columns=["race_key"])
        result = evaluate_roi(predictions, hjc, "fukusho_top3")
        assert result["race_count"] == 0
