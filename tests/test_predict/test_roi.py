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


@pytest.fixture
def ev_predictions_df():
    """Predictions with odds/fukusho_odds for EV strategy tests.

    R001 (7 horses):
      horse 3:  prob=0.75, odds=5.0, fukusho=2.5  → ev_tan=1.25, ev_fuku=1.875 (axis)
      horse 7:  prob=0.60, odds=6.0, fukusho=2.0  → ev_tan=1.20, ev_fuku=1.20  (axis)
      horse 1:  prob=0.25, odds=10.0, fukusho=3.0 → ev_tan=0.833, ev_fuku=0.75
      horse 9:  prob=0.20, odds=12.0, fukusho=4.0 → ev_tan=0.80, ev_fuku=0.80
      horse 14: prob=0.15, odds=15.0, fukusho=5.0 → ev_tan=0.75, ev_fuku=0.75
      horse 5:  prob=0.30, odds=7.0, fukusho=2.5  → ev_tan=0.70, ev_fuku=0.75
      horse 12: prob=0.40, odds=5.0, fukusho=1.8  → ev_tan=0.667, ev_fuku=0.72

    R002 (3 horses, axisless for ev_fuku>1.0):
      horse 1: prob=0.50, odds=3.0, fukusho=1.5   → ev_tan=0.50, ev_fuku=0.75
      horse 4: prob=0.40, odds=7.0, fukusho=2.0   → ev_tan=0.933, ev_fuku=0.80
      horse 8: prob=0.30, odds=12.0, fukusho=3.0  → ev_tan=1.20, ev_fuku=0.90
    """
    return pd.DataFrame({
        "race_key":     ["R001"] * 7 + ["R002"] * 3,
        "horse_number": [3, 7, 1, 9, 14, 5, 12, 1, 4, 8],
        "predict_prob": [0.75, 0.60, 0.25, 0.20, 0.15, 0.30, 0.40,
                         0.50, 0.40, 0.30],
        "odds":         [5.0, 6.0, 10.0, 12.0, 15.0, 7.0, 5.0,
                         3.0, 7.0, 12.0],
        "fukusho_odds": [2.5, 2.0, 3.0, 4.0, 5.0, 2.5, 1.8,
                         1.5, 2.0, 3.0],
    })


@pytest.fixture
def ev_hjc_df():
    """HJC payoff data aligned with ev_predictions_df.

    R001: horse 3 wins single, place winners are 3/7/1 (top 3 finish)
    R002: horse 8 wins single, place winners are 8/1/4 (ev_tansho on horse 8 hits)
    """
    data = {
        "race_key": ["R001", "R002"],
        # 単勝
        "単勝馬番_1": [3, 8],
        "単勝払戻_1": [500, 600],
        "単勝馬番_2": [0, 0],
        "単勝払戻_2": [0, 0],
        "単勝馬番_3": [0, 0],
        "単勝払戻_3": [0, 0],
        # 複勝
        "複勝馬番_1": [3, 8],
        "複勝払戻_1": [200, 250],
        "複勝馬番_2": [7, 1],
        "複勝払戻_2": [250, 150],
        "複勝馬番_3": [1, 4],
        "複勝払戻_3": [400, 200],
        "複勝馬番_4": [0, 0],
        "複勝払戻_4": [0, 0],
        "複勝馬番_5": [0, 0],
        "複勝払戻_5": [0, 0],
        # 三連複 (R001: {3,7,1} R002: different combo so nagashi misses if axis existed)
        "三連複組合せ_1": ["030701", "010408"],
        "三連複払戻_1": [3200, 4500],
        "三連複組合せ_2": ["", ""],
        "三連複払戻_2": [0, 0],
        "三連複組合せ_3": ["", ""],
        "三連複払戻_3": [0, 0],
    }
    return pd.DataFrame(data)


class TestEvTanshoStrategy:
    def test_threshold_filters_horses(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(ev_predictions_df, ev_hjc_df, "ev_tansho", ev_threshold=1.0)
        # R001: horses 3, 7 clear. R002: horse 8 clears. → 3 bets × ¥100 = ¥300
        assert result["total_bets"] == 300

    def test_hit_and_returns(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(ev_predictions_df, ev_hjc_df, "ev_tansho", ev_threshold=1.0)
        # R001: horse 3 wins → 500 (horse 7 misses). R002: horse 8 wins → 600.
        assert result["total_return"] == 500 + 600
        assert result["hit_count"] == 2

    def test_race_counts(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(ev_predictions_df, ev_hjc_df, "ev_tansho", ev_threshold=1.0)
        assert result["race_count"] == 2
        assert result["bet_race_count"] == 2

    def test_higher_threshold_reduces_bets(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(ev_predictions_df, ev_hjc_df, "ev_tansho", ev_threshold=1.22)
        # Only horse 3 (ev_tan=1.25) clears. R002 horse 8 (1.20) does not.
        assert result["total_bets"] == 100
        assert result["bet_race_count"] == 1

    def test_threshold_too_high_no_bets(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(ev_predictions_df, ev_hjc_df, "ev_tansho", ev_threshold=2.0)
        assert result["total_bets"] == 0
        assert result["bet_race_count"] == 0
        assert result["race_count"] == 2  # races still counted

    def test_result_schema(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(ev_predictions_df, ev_hjc_df, "ev_tansho", ev_threshold=1.0)
        assert result["strategy"] == "ev_tansho"
        assert result["ev_threshold"] == 1.0
        assert "bet_race_count" in result


class TestEvFukushoStrategy:
    def test_threshold_filters_horses(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(ev_predictions_df, ev_hjc_df, "ev_fukusho", ev_threshold=1.0)
        # R001: horses 3 (ev_fuku=1.875), 7 (1.20) clear. R002: none clear.
        assert result["total_bets"] == 200
        assert result["bet_race_count"] == 1
        assert result["race_count"] == 2

    def test_returns(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(ev_predictions_df, ev_hjc_df, "ev_fukusho", ev_threshold=1.0)
        # horse 3 → 200, horse 7 → 250
        assert result["total_return"] == 200 + 250
        assert result["hit_count"] == 2

    def test_nan_fukusho_odds_excluded(self, ev_hjc_df):
        predictions = pd.DataFrame({
            "race_key": ["R001"] * 2,
            "horse_number": [3, 7],
            "predict_prob": [0.75, 0.60],
            "odds": [5.0, 6.0],
            "fukusho_odds": [pd.NA, 2.0],  # horse 3 missing odds → ev_fuku=NaN
        })
        result = evaluate_roi(predictions, ev_hjc_df, "ev_fukusho", ev_threshold=1.0)
        # Only horse 7 qualifies; horse 3 excluded by NaN.
        assert result["total_bets"] == 100
        assert result["total_return"] == 250  # horse 7 place payout


class TestEvSanrenpukuNagashiStrategy:
    def test_axisless_race_skipped(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(
            ev_predictions_df, ev_hjc_df, "ev_sanrenpuku_nagashi", ev_threshold=1.0,
        )
        # R002 has no horse with ev_fuku > 1.0 AND only 3 horses total.
        # Only R001 can bet: axes = [3, 7], each 10 combos × ¥100 = ¥1000/axis.
        assert result["bet_race_count"] == 1
        assert result["race_count"] == 2

    def test_multi_axis_doubles_stake(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(
            ev_predictions_df, ev_hjc_df, "ev_sanrenpuku_nagashi", ev_threshold=1.0,
        )
        # 2 axes in R001 × 10 combos × ¥100 = ¥2000
        assert result["total_bets"] == 2000

    def test_hit_both_axes(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(
            ev_predictions_df, ev_hjc_df, "ev_sanrenpuku_nagashi", ev_threshold=1.0,
        )
        # R001 top 3 = {3, 7, 1}, axis 3 has partner 7+1 → hit, axis 7 has partner 3+1 → hit.
        # Both collect the ¥3200 payoff.
        assert result["total_return"] == 3200 * 2
        assert result["hit_count"] == 2

    def test_details_axes_recorded(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(
            ev_predictions_df, ev_hjc_df, "ev_sanrenpuku_nagashi", ev_threshold=1.0,
        )
        r001 = next(d for d in result["details"] if d["race_key"] == "R001")
        assert set(r001["axes"]) == {3, 7}
        assert r001["combos"] == 20  # 2 axes × C(5,2)

    def test_single_axis(self, ev_predictions_df, ev_hjc_df):
        result = evaluate_roi(
            ev_predictions_df, ev_hjc_df, "ev_sanrenpuku_nagashi", ev_threshold=1.5,
        )
        # Only horse 3 (ev_fuku=1.875) clears. 10 combos × ¥100 = ¥1000.
        assert result["total_bets"] == 1000
        # Winning set {3,7,1}: axis 3 with partners (top 5 by ev_tan excluding 3) hits.
        assert result["total_return"] == 3200
        assert result["hit_count"] == 1


class TestEvThresholdSensitivity:
    def test_non_ev_strategy_ignores_threshold(self, predictions_df, hjc_df):
        """Passing ev_threshold to a non-EV strategy must not change results."""
        base = evaluate_roi(predictions_df, hjc_df, "fukusho_top3")
        with_threshold = evaluate_roi(
            predictions_df, hjc_df, "fukusho_top3", ev_threshold=5.0,
        )
        assert base["total_bets"] == with_threshold["total_bets"]
        assert base["total_return"] == with_threshold["total_return"]
        assert base["roi"] == with_threshold["roi"]


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
