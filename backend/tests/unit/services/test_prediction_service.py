"""Tests for prediction service."""

from unittest.mock import MagicMock, patch

import pytest

from app.ml.pace import PaceResult
from app.models import RaceEntry, RunningStyle
from app.schemas import HorsePrediction, PacePrediction
from app.services.prediction_service import HorseAnalysis, PredictionService


class TestHorseAnalysis:
    """Tests for HorseAnalysis dataclass and _analyze_all_horses method."""

    def test_horse_analysis_creation(self):
        """Verify HorseAnalysis can be created with all fields."""
        analysis = HorseAnalysis(
            horse_id=1,
            horse_name="テストホース",
            horse_number=1,
            running_style="ESCAPE",
            avg_first_corner=1.5,
            avg_last_3f=33.5,
            best_last_3f=33.0,
            win_rate=0.15,
            place_rate=0.35,
            grade_race_wins=2,
            odds=5.0,
            popularity=1,
        )

        assert analysis.horse_id == 1
        assert analysis.horse_name == "テストホース"
        assert analysis.running_style == "ESCAPE"
        assert analysis.avg_first_corner == 1.5
        assert analysis.best_last_3f == 33.0

    @pytest.mark.asyncio
    async def test_analyze_all_horses_running_style_mapping(self, db_session, test_race, test_entries):
        """Verify running style to corner position mapping."""
        service = PredictionService(db_session)
        analyses = await service._analyze_all_horses(test_entries, "G1")

        # Check style to corner mapping
        style_corners = {
            "ESCAPE": 1.5,
            "FRONT": 4.0,
            "STALKER": 7.0,
            "CLOSER": 12.0,
            "VERSATILE": 8.0,
        }

        for entry in test_entries:
            if entry.horse_id in analyses:
                analysis = analyses[entry.horse_id]
                expected_corner = style_corners.get(analysis.running_style, 8.0)
                assert analysis.avg_first_corner == expected_corner

    @pytest.mark.asyncio
    async def test_analyze_all_horses_popularity_based_last_3f(self, db_session, test_race, test_entries):
        """Top 3 popular horses get 33.5s avg, 6+ get 34.5s."""
        service = PredictionService(db_session)
        analyses = await service._analyze_all_horses(test_entries, "G1")

        for entry in test_entries:
            if entry.horse_id in analyses:
                analysis = analyses[entry.horse_id]
                popularity = entry.popularity or 10

                if popularity <= 3:
                    assert analysis.avg_last_3f == 33.5
                    assert analysis.best_last_3f == 33.0
                elif popularity <= 6:
                    assert analysis.avg_last_3f == 34.0
                    assert analysis.best_last_3f == 33.5
                else:
                    assert analysis.avg_last_3f == 34.5
                    assert analysis.best_last_3f == 34.0

    @pytest.mark.asyncio
    async def test_analyze_all_horses_odds_to_win_rate(self, db_session, test_race, test_entries):
        """win_rate = min(1.0/odds, 0.5)"""
        service = PredictionService(db_session)
        analyses = await service._analyze_all_horses(test_entries, "G1")

        for entry in test_entries:
            if entry.horse_id in analyses and entry.odds:
                analysis = analyses[entry.horse_id]
                expected_win_rate = min(1.0 / entry.odds, 0.5)
                assert abs(analysis.win_rate - expected_win_rate) < 0.001

    @pytest.mark.asyncio
    async def test_analyze_all_horses_g1_grade_race_wins(self, db_session, test_race, test_entries):
        """G1: top 10 popularity have wins."""
        service = PredictionService(db_session)
        analyses = await service._analyze_all_horses(test_entries, "G1")

        for entry in test_entries:
            if entry.horse_id in analyses:
                analysis = analyses[entry.horse_id]
                popularity = entry.popularity or 10

                if popularity <= 10:
                    assert analysis.grade_race_wins >= 1
                else:
                    assert analysis.grade_race_wins == 0

    @pytest.mark.asyncio
    async def test_analyze_all_horses_g3_grade_race_wins(self, db_session, test_race, test_entries):
        """G3: only top 5 popularity have wins."""
        service = PredictionService(db_session)
        analyses = await service._analyze_all_horses(test_entries, "G3")

        for entry in test_entries:
            if entry.horse_id in analyses:
                analysis = analyses[entry.horse_id]
                popularity = entry.popularity or 10

                if popularity <= 5:
                    assert analysis.grade_race_wins >= 1
                else:
                    assert analysis.grade_race_wins == 0


class TestEstimateRunningStyle:
    """Tests for _estimate_running_style_from_avg method."""

    def test_escape_estimation(self, db_session):
        """Average corner <= 2.5 should be ESCAPE."""
        service = PredictionService(db_session)
        assert service._estimate_running_style_from_avg(1.5) == "ESCAPE"
        assert service._estimate_running_style_from_avg(2.0) == "ESCAPE"
        assert service._estimate_running_style_from_avg(2.5) == "ESCAPE"

    def test_front_estimation(self, db_session):
        """Average corner 2.5-5.0 should be FRONT."""
        service = PredictionService(db_session)
        assert service._estimate_running_style_from_avg(3.0) == "FRONT"
        assert service._estimate_running_style_from_avg(4.0) == "FRONT"
        assert service._estimate_running_style_from_avg(5.0) == "FRONT"

    def test_stalker_estimation(self, db_session):
        """Average corner 5.0-10.0 should be STALKER."""
        service = PredictionService(db_session)
        assert service._estimate_running_style_from_avg(6.0) == "STALKER"
        assert service._estimate_running_style_from_avg(8.0) == "STALKER"
        assert service._estimate_running_style_from_avg(10.0) == "STALKER"

    def test_closer_estimation(self, db_session):
        """Average corner > 10.0 should be CLOSER."""
        service = PredictionService(db_session)
        assert service._estimate_running_style_from_avg(11.0) == "CLOSER"
        assert service._estimate_running_style_from_avg(15.0) == "CLOSER"


class TestPaceScoreCalculation:
    """Tests for _calculate_pace_score method."""

    def test_advantageous_style_bonus(self, db_session):
        """First advantage style gets 0.35 base."""
        service = PredictionService(db_session)

        analysis = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=5,
        )
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )

        score = service._calculate_pace_score(analysis, pace, None, None)
        # First in advantage list = 0.35 base
        assert score >= 0.30

    def test_non_advantageous_style_low_score(self, db_session):
        """Non-advantageous style gets lower base score."""
        service = PredictionService(db_session)

        analysis = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="ESCAPE",
            avg_first_corner=1.5, avg_last_3f=34.0, best_last_3f=34.0,
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=5,
        )
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )

        score = service._calculate_pace_score(analysis, pace, None, None)
        # Not advantageous = 0.1 base
        assert score <= 0.2

    def test_high_pace_last_3f_bonus(self, db_session):
        """High pace + best_last_3f <= 33.5 gives +0.1 bonus."""
        service = PredictionService(db_session)

        # Horse with good last 3f
        analysis_good = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=33.0, best_last_3f=33.0,
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=5,
        )
        # Horse with average last 3f
        analysis_avg = HorseAnalysis(
            horse_id=2, horse_name="Test2", horse_number=2,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=35.0, best_last_3f=34.5,
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=6,
        )
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )

        score_good = service._calculate_pace_score(analysis_good, pace, None, None)
        score_avg = service._calculate_pace_score(analysis_avg, pace, None, None)

        # Good last 3f horse should score higher
        assert score_good > score_avg

    def test_slow_pace_position_bonus(self, db_session):
        """Slow pace + good position (avg_first_corner <= 5) gives bonus."""
        service = PredictionService(db_session)

        # Good position horse
        analysis_front = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="FRONT",
            avg_first_corner=4.0, avg_last_3f=34.0, best_last_3f=34.0,
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=5,
        )
        # Back position horse
        analysis_back = HorseAnalysis(
            horse_id=2, horse_name="Test2", horse_number=2,
            running_style="FRONT",
            avg_first_corner=6.0, avg_last_3f=34.0, best_last_3f=34.0,
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=6,
        )
        pace = PacePrediction(
            type="slow", confidence=0.8, reason="test",
            advantageous_styles=["ESCAPE", "FRONT"],
            escape_count=1, front_count=2,
        )

        score_front = service._calculate_pace_score(analysis_front, pace, None, None)
        score_back = service._calculate_pace_score(analysis_back, pace, None, None)

        # Front position horse gets bonus in slow pace
        assert score_front > score_back

    def test_score_bounds(self, db_session):
        """Score should be bounded between 0.05 and 0.5."""
        service = PredictionService(db_session)

        analysis = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
            win_rate=0.5, place_rate=0.8, grade_race_wins=5,
            odds=2.0, popularity=1,
        )
        pace = PacePrediction(
            type="high", confidence=1.0, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=5, front_count=2,
        )

        score = service._calculate_pace_score(analysis, pace, None, None)
        assert 0.05 <= score <= 0.5


class TestLast3fScoreCalculation:
    """Tests for _calculate_last_3f_score method."""

    def test_excellent_last_3f(self, db_session):
        """best_last_3f <= 32.5 should get highest score."""
        service = PredictionService(db_session)

        analysis = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=32.5, best_last_3f=32.0,
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=5,
        )
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )

        score = service._calculate_last_3f_score(analysis, pace)
        # Base score 0.35 * stability (avg-best=0.5 gap) -> ~0.26
        assert score >= 0.25

    def test_poor_last_3f(self, db_session):
        """best_last_3f > 34.5 should get lowest score."""
        service = PredictionService(db_session)

        analysis = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=36.0, best_last_3f=35.5,
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=5,
        )
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )

        score = service._calculate_last_3f_score(analysis, pace)
        assert score <= 0.15

    def test_high_pace_multiplier(self, db_session):
        """High pace should increase last 3f score by 1.2x."""
        service = PredictionService(db_session)

        analysis = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=33.5, best_last_3f=33.0,
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=5,
        )
        pace_high = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )
        pace_slow = PacePrediction(
            type="slow", confidence=0.8, reason="test",
            advantageous_styles=["ESCAPE", "FRONT"],
            escape_count=1, front_count=2,
        )

        score_high = service._calculate_last_3f_score(analysis, pace_high)
        score_slow = service._calculate_last_3f_score(analysis, pace_slow)

        # High pace should give higher score
        assert score_high > score_slow

    def test_stability_factor(self, db_session):
        """Stable horse (small avg-best gap) should score higher."""
        service = PredictionService(db_session)

        # Stable horse
        analysis_stable = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=33.5, best_last_3f=33.0,  # 0.5 gap
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=5,
        )
        # Unstable horse
        analysis_unstable = HorseAnalysis(
            horse_id=2, horse_name="Test2", horse_number=2,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=35.0, best_last_3f=33.0,  # 2.0 gap
            win_rate=0.1, place_rate=0.3, grade_race_wins=0,
            odds=10.0, popularity=6,
        )
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )

        score_stable = service._calculate_last_3f_score(analysis_stable, pace)
        score_unstable = service._calculate_last_3f_score(analysis_unstable, pace)

        assert score_stable > score_unstable


class TestTrackRecordScoreCalculation:
    """Tests for _calculate_track_record_score method."""

    def test_high_win_rate_bonus(self, db_session):
        """High win rate should increase score."""
        service = PredictionService(db_session)

        analysis_high = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
            win_rate=0.30, place_rate=0.50, grade_race_wins=2,
            odds=3.0, popularity=1,
        )
        analysis_low = HorseAnalysis(
            horse_id=2, horse_name="Test2", horse_number=2,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
            win_rate=0.05, place_rate=0.15, grade_race_wins=0,
            odds=50.0, popularity=10,
        )

        score_high = service._calculate_track_record_score(analysis_high)
        score_low = service._calculate_track_record_score(analysis_low)

        assert score_high > score_low

    def test_grade_race_wins_bonus(self, db_session):
        """Grade race wins should add to score."""
        service = PredictionService(db_session)

        # 3+ grade wins
        analysis_3wins = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
            win_rate=0.15, place_rate=0.35, grade_race_wins=3,
            odds=5.0, popularity=2,
        )
        # 1 grade win
        analysis_1win = HorseAnalysis(
            horse_id=2, horse_name="Test2", horse_number=2,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
            win_rate=0.15, place_rate=0.35, grade_race_wins=1,
            odds=8.0, popularity=4,
        )
        # 0 grade wins
        analysis_0wins = HorseAnalysis(
            horse_id=3, horse_name="Test3", horse_number=3,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
            win_rate=0.15, place_rate=0.35, grade_race_wins=0,
            odds=15.0, popularity=6,
        )

        score_3 = service._calculate_track_record_score(analysis_3wins)
        score_1 = service._calculate_track_record_score(analysis_1win)
        score_0 = service._calculate_track_record_score(analysis_0wins)

        assert score_3 > score_1 > score_0

    def test_score_bounded_at_0_4(self, db_session):
        """Score should be bounded at 0.4."""
        service = PredictionService(db_session)

        # Max values
        analysis = HorseAnalysis(
            horse_id=1, horse_name="Test", horse_number=1,
            running_style="STALKER",
            avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
            win_rate=0.50, place_rate=0.80, grade_race_wins=10,
            odds=2.0, popularity=1,
        )

        score = service._calculate_track_record_score(analysis)
        assert score <= 0.4


class TestDarkHorseDetection:
    """Tests for dark horse detection in rankings."""

    @pytest.mark.asyncio
    async def test_dark_horse_criteria(self, db_session, test_race, test_entries):
        """Popularity >= 6 and score >= 0.15 should be dark horse."""
        service = PredictionService(db_session)

        # Get analyses
        analyses = await service._analyze_all_horses(test_entries, "G1")

        # Create pace prediction
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=2, front_count=2,
        )

        # Generate rankings
        rankings, _ = service._generate_rankings_with_pace(test_entries, analyses, pace, test_race)

        # Check dark horse detection
        for r in rankings:
            if r.is_dark_horse:
                assert r.popularity is None or r.popularity >= 6
                assert r.score >= 0.15


class TestBetGeneration:
    """Tests for _generate_bets method."""

    def test_trifecta_formation(self, db_session):
        """Trifecta uses top 2 as axis, counter horses 2-6."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=i+1, horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                score=0.3 - i*0.02, win_probability=0.2, place_probability=0.4,
                popularity=i+1, odds=float(3+i*2), is_dark_horse=False,
            )
            for i in range(10)
        ]
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )
        analyses = {}

        bets = service._generate_bets(rankings, pace, analyses, None)

        assert bets.trifecta is not None
        assert bets.trifecta["type"] == "formation"
        assert 1 in bets.trifecta["first"]  # Top horse as axis
        assert 2 in bets.trifecta["first"]  # Second horse as axis

    def test_trio_box_combinations(self, db_session):
        """Trio box with 5 horses = 10 combinations."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=i+1, horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                score=0.3 - i*0.02, win_probability=0.2, place_probability=0.4,
                popularity=i+1, odds=float(3+i*2), is_dark_horse=False,
            )
            for i in range(10)
        ]
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )
        analyses = {}

        bets = service._generate_bets(rankings, pace, analyses, None)

        assert bets.trio is not None
        assert bets.trio["type"] == "box"
        assert bets.trio["combinations"] == 10

    def test_exacta_generation_high_confidence(self, db_session):
        """Exacta only when top horse score > 0.25."""
        service = PredictionService(db_session)

        # High score top horse
        rankings_high = [
            HorsePrediction(
                rank=1, horse_id=1, horse_name="本命馬", horse_number=1,
                score=0.35, win_probability=0.25, place_probability=0.5,
                popularity=1, odds=3.0, is_dark_horse=False,
            ),
        ] + [
            HorsePrediction(
                rank=i+2, horse_id=i+2, horse_name=f"馬{i+2}", horse_number=i+2,
                score=0.2 - i*0.02, win_probability=0.1, place_probability=0.3,
                popularity=i+2, odds=float(5+i*3), is_dark_horse=False,
            )
            for i in range(9)
        ]
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )

        bets = service._generate_bets(rankings_high, pace, {}, None)
        assert bets.exacta is not None
        assert bets.exacta["first"] == 1

    def test_exacta_not_generated_low_confidence(self, db_session):
        """Exacta not generated when top horse score <= 0.25."""
        service = PredictionService(db_session)

        # Low score top horse
        rankings_low = [
            HorsePrediction(
                rank=i+1, horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                score=0.2 - i*0.01, win_probability=0.1, place_probability=0.3,
                popularity=i+1, odds=float(5+i*3), is_dark_horse=False,
            )
            for i in range(10)
        ]
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )

        bets = service._generate_bets(rankings_low, pace, {}, None)
        assert bets.exacta is None

    def test_total_investment_calculation(self, db_session):
        """Total investment should be calculated correctly."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=i+1, horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                score=0.3 - i*0.02, win_probability=0.2, place_probability=0.4,
                popularity=i+1, odds=float(3+i*2), is_dark_horse=(i >= 5),
                dark_horse_reason="穴馬" if i >= 5 else None,
            )
            for i in range(10)
        ]
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )

        bets = service._generate_bets(rankings, pace, {}, None)

        # Verify total is sum of all bets
        expected_total = (
            bets.trifecta["combinations"] * bets.trifecta["amount_per_ticket"]
            + bets.trio["combinations"] * bets.trio["amount_per_ticket"]
        )
        if bets.exacta:
            expected_total += bets.exacta["combinations"] * bets.exacta["amount_per_ticket"]
        if bets.wide:
            expected_total += len(bets.wide["pairs"]) * bets.wide["amount_per_ticket"]

        assert bets.total_investment == expected_total


class TestHighRiskBetGeneration:
    """Tests for _generate_high_risk_bets method."""

    def test_high_risk_single_bet(self, db_session):
        """Single bet on highest expected return dark horse."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=i+1, horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                score=0.3 - i*0.02, win_probability=0.2, place_probability=0.4,
                popularity=i+1, odds=float(3+i*5), is_dark_horse=(i >= 5),
            )
            for i in range(10)
        ]
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )
        analyses = {
            i+1: HorseAnalysis(
                horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                running_style="STALKER" if i >= 5 else "FRONT",
                avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
                win_rate=0.1, place_rate=0.3, grade_race_wins=0,
                odds=float(3+i*5), popularity=i+1,
            )
            for i in range(10)
        }

        high_risk = service._generate_high_risk_bets(rankings, pace, analyses)

        # Should have at least one single bet
        single_bets = [b for b in high_risk if b.bet_type == "単勝"]
        assert len(single_bets) >= 1

    def test_high_risk_wide_bet(self, db_session):
        """Wide bet pairing dark horse with favorite."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=i+1, horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                score=0.3 - i*0.02, win_probability=0.2, place_probability=0.4,
                popularity=i+1, odds=float(3+i*5), is_dark_horse=(i >= 5),
            )
            for i in range(10)
        ]
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )
        analyses = {
            i+1: HorseAnalysis(
                horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                running_style="STALKER" if i >= 5 else "FRONT",
                avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
                win_rate=0.1, place_rate=0.3, grade_race_wins=0,
                odds=float(3+i*5), popularity=i+1,
            )
            for i in range(10)
        }

        high_risk = service._generate_high_risk_bets(rankings, pace, analyses)

        # Should have wide bet
        wide_bets = [b for b in high_risk if b.bet_type == "ワイド"]
        assert len(wide_bets) >= 1

    def test_sorted_by_expected_return(self, db_session):
        """High risk bets should be sorted by expected return."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=i+1, horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                score=0.25 - i*0.01, win_probability=0.2, place_probability=0.4,
                popularity=i+1, odds=float(3+i*10), is_dark_horse=(i >= 5),
            )
            for i in range(10)
        ]
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )
        analyses = {
            i+1: HorseAnalysis(
                horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                running_style="STALKER" if i >= 5 else "FRONT",
                avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
                win_rate=0.1, place_rate=0.3, grade_race_wins=0,
                odds=float(3+i*10), popularity=i+1,
            )
            for i in range(10)
        }

        high_risk = service._generate_high_risk_bets(rankings, pace, analyses)

        # Verify sorted by expected return (descending)
        for i in range(len(high_risk) - 1):
            assert high_risk[i].expected_return >= high_risk[i+1].expected_return


class TestConfidenceCalculation:
    """Tests for _calculate_confidence method."""

    def test_confidence_from_pace(self, db_session):
        """Pace confidence contributes 40%."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=1, horse_id=1, horse_name="馬1", horse_number=1,
                score=0.3, win_probability=0.2, place_probability=0.4,
                popularity=1, odds=3.0, is_dark_horse=False,
            ),
            HorsePrediction(
                rank=2, horse_id=2, horse_name="馬2", horse_number=2,
                score=0.25, win_probability=0.15, place_probability=0.35,
                popularity=2, odds=5.0, is_dark_horse=False,
            ),
        ]
        pace_high = PacePrediction(
            type="high", confidence=0.9, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )
        pace_low = PacePrediction(
            type="middle", confidence=0.5, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )
        analyses = {}

        conf_high = service._calculate_confidence(rankings, pace_high, analyses)
        conf_low = service._calculate_confidence(rankings, pace_low, analyses)

        # Higher pace confidence should result in higher overall confidence
        assert conf_high > conf_low

    def test_score_diff_bonus(self, db_session):
        """Large score diff between 1st and 2nd increases confidence."""
        service = PredictionService(db_session)

        # Large gap
        rankings_gap = [
            HorsePrediction(
                rank=1, horse_id=1, horse_name="馬1", horse_number=1,
                score=0.4, win_probability=0.25, place_probability=0.5,
                popularity=1, odds=2.5, is_dark_horse=False,
            ),
            HorsePrediction(
                rank=2, horse_id=2, horse_name="馬2", horse_number=2,
                score=0.2, win_probability=0.1, place_probability=0.3,
                popularity=2, odds=6.0, is_dark_horse=False,
            ),
        ]
        # Small gap
        rankings_close = [
            HorsePrediction(
                rank=1, horse_id=1, horse_name="馬1", horse_number=1,
                score=0.25, win_probability=0.15, place_probability=0.35,
                popularity=1, odds=4.0, is_dark_horse=False,
            ),
            HorsePrediction(
                rank=2, horse_id=2, horse_name="馬2", horse_number=2,
                score=0.24, win_probability=0.14, place_probability=0.34,
                popularity=2, odds=4.5, is_dark_horse=False,
            ),
        ]
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )
        analyses = {}

        conf_gap = service._calculate_confidence(rankings_gap, pace, analyses)
        conf_close = service._calculate_confidence(rankings_close, pace, analyses)

        assert conf_gap > conf_close

    def test_empty_rankings_returns_zero(self, db_session):
        """Empty rankings should return 0 confidence."""
        service = PredictionService(db_session)

        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )

        conf = service._calculate_confidence([], pace, {})
        assert conf == 0.0

    def test_confidence_bounded_at_1(self, db_session):
        """Confidence should be bounded at 1.0."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=1, horse_id=1, horse_name="馬1", horse_number=1,
                score=0.5, win_probability=0.3, place_probability=0.6,
                popularity=1, odds=2.0, is_dark_horse=False,
            ),
            HorsePrediction(
                rank=2, horse_id=2, horse_name="馬2", horse_number=2,
                score=0.1, win_probability=0.05, place_probability=0.2,
                popularity=10, odds=50.0, is_dark_horse=False,
            ),
        ]
        pace = PacePrediction(
            type="high", confidence=1.0, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=5, front_count=2,
        )
        analyses = {
            1: HorseAnalysis(
                horse_id=1, horse_name="馬1", horse_number=1,
                running_style="STALKER",
                avg_first_corner=7.0, avg_last_3f=32.0, best_last_3f=31.5,
                win_rate=0.3, place_rate=0.6, grade_race_wins=5,
                odds=2.0, popularity=1,
            )
        }

        conf = service._calculate_confidence(rankings, pace, analyses)
        assert conf <= 1.0


class TestReasoningGeneration:
    """Tests for _generate_reasoning method."""

    def test_reasoning_pace_description(self, db_session):
        """High/middle/slow pace generates correct Japanese text."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=1, horse_id=1, horse_name="本命馬", horse_number=1,
                score=0.3, win_probability=0.2, place_probability=0.4,
                popularity=1, odds=3.0, is_dark_horse=False,
            ),
        ]
        analyses = {
            1: HorseAnalysis(
                horse_id=1, horse_name="本命馬", horse_number=1,
                running_style="STALKER",
                avg_first_corner=7.0, avg_last_3f=33.5, best_last_3f=33.0,
                win_rate=0.2, place_rate=0.4, grade_race_wins=2,
                odds=3.0, popularity=1,
            )
        }

        # High pace
        pace_high = PacePrediction(
            type="high", confidence=0.85, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )
        reasoning_high = service._generate_reasoning(rankings, pace_high, analyses)
        assert "ハイペース" in reasoning_high

        # Slow pace
        pace_slow = PacePrediction(
            type="slow", confidence=0.8, reason="test",
            advantageous_styles=["ESCAPE", "FRONT"],
            escape_count=1, front_count=2,
        )
        reasoning_slow = service._generate_reasoning(rankings, pace_slow, analyses)
        assert "スローペース" in reasoning_slow

    def test_reasoning_ml_annotation(self, db_session):
        """ML usage adds '※ AI予測モデル' note."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=1, horse_id=1, horse_name="本命馬", horse_number=1,
                score=0.3, win_probability=0.2, place_probability=0.4,
                popularity=1, odds=3.0, is_dark_horse=False,
            ),
        ]
        analyses = {
            1: HorseAnalysis(
                horse_id=1, horse_name="本命馬", horse_number=1,
                running_style="STALKER",
                avg_first_corner=7.0, avg_last_3f=33.5, best_last_3f=33.0,
                win_rate=0.2, place_rate=0.4, grade_race_wins=2,
                odds=3.0, popularity=1,
            )
        }
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )

        # With ML
        reasoning_ml = service._generate_reasoning(rankings, pace, analyses, use_ml=True)
        assert "AI予測モデル" in reasoning_ml

        # Without ML
        reasoning_no_ml = service._generate_reasoning(rankings, pace, analyses, use_ml=False)
        assert "AI予測モデル" not in reasoning_no_ml

    def test_reasoning_empty_rankings(self, db_session):
        """Empty rankings should return data insufficient message."""
        service = PredictionService(db_session)

        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )

        reasoning = service._generate_reasoning([], pace, {})
        assert "データ不足" in reasoning

    def test_reasoning_contains_sections(self, db_session):
        """Reasoning should contain all expected sections."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=i+1, horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                score=0.3 - i*0.02, win_probability=0.2, place_probability=0.4,
                popularity=i+1, odds=float(3+i*2), is_dark_horse=(i >= 5),
                dark_horse_reason="展開向く" if i >= 5 else None,
            )
            for i in range(10)
        ]
        analyses = {
            i+1: HorseAnalysis(
                horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                running_style="STALKER" if i >= 5 else "FRONT",
                avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
                win_rate=0.1, place_rate=0.3, grade_race_wins=0,
                odds=float(3+i*2), popularity=i+1,
            )
            for i in range(10)
        }
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3, front_count=2,
        )

        reasoning = service._generate_reasoning(rankings, pace, analyses)

        # Check for expected sections
        assert "■ 展開予想" in reasoning
        assert "■ 本命" in reasoning
        assert "■ 対抗・単穴" in reasoning
        assert "■ 穴馬注目" in reasoning
        assert "■ 買い目のポイント" in reasoning
