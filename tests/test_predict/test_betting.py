"""Tests for EV-based betting recommendations."""
import pandas as pd

from src.predict.betting import (
    compute_expected_values,
    recommend_bets,
    recommend_nagashi,
)


def _race_df() -> pd.DataFrame:
    return pd.DataFrame({
        "horse_number": [1, 2, 3, 4],
        "horse_name": ["A", "B", "C", "D"],
        "odds": [2.0, 5.0, 10.0, 20.0],
        "fukusho_odds": [1.2, 2.0, 3.0, 6.0],
    })


class TestComputeExpectedValues:
    def test_ev_math(self):
        preds = [0.6, 0.3, 0.2, 0.05]
        ev = compute_expected_values(_race_df(), preds)

        # ev_tan = (is_place / 3) * odds
        # horse 1: 0.2*2.0=0.4, horse 2: 0.1*5.0=0.5, horse 3: 0.0667*10=0.667, horse 4: 0.0167*20=0.333
        assert list(ev["horse_number"]) == [3, 2, 1, 4]
        assert ev.iloc[0]["ev_tan"] == (0.2 / 3.0) * 10.0
        # ev_fuku = is_place * fukusho_odds
        assert ev.iloc[0]["ev_fuku"] == 0.2 * 3.0

    def test_missing_fukusho_odds(self):
        df = _race_df().drop(columns=["fukusho_odds"])
        ev = compute_expected_values(df, [0.5, 0.3, 0.2, 0.0])
        # fukusho_odds column exists but values are NA → ev_fuku is NaN
        assert "ev_fuku" in ev.columns
        assert ev["ev_fuku"].isna().all()


class TestRecommendBets:
    def test_tansho_threshold(self):
        # ev_tan: h1=0.4, h2=0.5, h3=0.667, h4=0.333 → none > 1.0
        preds = [0.6, 0.3, 0.2, 0.05]
        ev = compute_expected_values(_race_df(), preds)
        bets = recommend_bets(ev, ev_threshold=1.0)
        assert bets["tansho"] == []

        bets_lo = recommend_bets(ev, ev_threshold=0.4)
        # > 0.4: h3(0.667), h2(0.5) → horses 3, 2
        assert sorted(bets_lo["tansho"]) == [2, 3]

    def test_fukusho_picks(self):
        # ev_fuku: 0.72, 0.6, 0.6, 0.3 — none over 1.0
        preds = [0.6, 0.3, 0.2, 0.05]
        ev = compute_expected_values(_race_df(), preds)
        bets = recommend_bets(ev, ev_threshold=1.0)
        assert bets["fukusho"] == []

        # Lower threshold — should now pick top few
        bets_lo = recommend_bets(ev, ev_threshold=0.5)
        assert 1 in bets_lo["fukusho"]

    def test_umaren_box_pairs(self):
        preds = [0.6, 0.3, 0.2, 0.05]
        ev = compute_expected_values(_race_df(), preds)
        bets = recommend_bets(ev, box_size=3)
        # Top 3 by ev_tan: horses 3, 2, 1 → sorted combos: (1,2), (1,3), (2,3)
        assert bets["umaren_box"] == [(1, 2), (1, 3), (2, 3)]

    def test_sanrenpuku_box(self):
        preds = [0.6, 0.3, 0.2, 0.05]
        ev = compute_expected_values(_race_df(), preds)
        bets = recommend_bets(ev, trifecta_box_size=4)
        # Top 4 → C(4,3) = 4 combos
        assert len(bets["sanrenpuku_box"]) == 4

    def test_empty_df(self):
        ev = pd.DataFrame(columns=["horse_number", "ev_tan", "ev_fuku"])
        bets = recommend_bets(ev)
        assert bets == {
            "tansho": [], "fukusho": [],
            "umaren_box": [], "sanrenpuku_box": [],
        }


class TestRecommendNagashi:
    def test_axis_and_partners(self):
        # ev_fuku: h1=0.6*1.2=0.72, h2=0.3*2=0.6, h3=0.2*3=0.6, h4=0.05*6=0.3
        # ev_tan:  h1=0.4, h2=0.5, h3=0.667, h4=0.333
        # axis_criteria=ev_fuku threshold=0.5 → top: h1(0.72) clears
        preds = [0.6, 0.3, 0.2, 0.05]
        ev = compute_expected_values(_race_df(), preds)
        result = recommend_nagashi(
            ev,
            axis_criteria="ev_fuku",
            axis_threshold=0.5,
            partner_criteria="ev_tan",
            max_partners=3,
        )
        assert result["axis"] == 1
        # Partners (excluding axis=1) by ev_tan desc: h3(0.667), h2(0.5), h4(0.333)
        assert result["partners"] == [3, 2, 4]
        # Combos: axis=1 + every pair from partners → C(3,2)=3
        assert sorted(result["combos"]) == [(1, 2, 3), (1, 2, 4), (1, 3, 4)]

    def test_no_axis_returns_none(self):
        # All ev_fuku < 1.0 → no axis qualifies
        preds = [0.6, 0.3, 0.2, 0.05]
        ev = compute_expected_values(_race_df(), preds)
        result = recommend_nagashi(ev, axis_criteria="ev_fuku", axis_threshold=1.0)
        assert result == {"axis": None, "partners": [], "combos": []}

    def test_max_partners_cap(self):
        preds = [0.6, 0.3, 0.2, 0.05]
        ev = compute_expected_values(_race_df(), preds)
        result = recommend_nagashi(
            ev,
            axis_criteria="ev_fuku",
            axis_threshold=0.5,
            partner_criteria="ev_tan",
            max_partners=2,
        )
        assert result["axis"] == 1
        # Top 2 partners by ev_tan: h3(0.667), h2(0.5)
        assert result["partners"] == [3, 2]
        assert result["combos"] == [(1, 2, 3)]

    def test_empty_df(self):
        ev = pd.DataFrame(columns=["horse_number", "ev_tan", "ev_fuku"])
        result = recommend_nagashi(ev)
        assert result == {"axis": None, "partners": [], "combos": []}
