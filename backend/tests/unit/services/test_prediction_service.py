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
    async def test_analyze_all_horses_default_last_3f(self, db_session, test_race, test_entries):
        """All horses should have same default last_3f (no odds bias)."""
        service = PredictionService(db_session)
        analyses = await service._analyze_all_horses(test_entries, "G1")

        for entry in test_entries:
            if entry.horse_id in analyses:
                analysis = analyses[entry.horse_id]
                # 全馬同じデフォルト値（オッズ依存なし）
                assert analysis.avg_last_3f == 34.0
                assert analysis.best_last_3f == 33.5

    @pytest.mark.asyncio
    async def test_analyze_all_horses_default_win_rate(self, db_session, test_race, test_entries):
        """All horses should have same default win_rate (no odds bias)."""
        service = PredictionService(db_session)
        analyses = await service._analyze_all_horses(test_entries, "G1")

        for entry in test_entries:
            if entry.horse_id in analyses:
                analysis = analyses[entry.horse_id]
                # 全馬同じデフォルト値（オッズ依存なし）
                assert analysis.win_rate == 0.10
                assert analysis.place_rate == 0.25

    @pytest.mark.asyncio
    async def test_analyze_all_horses_default_grade_wins(self, db_session, test_race, test_entries):
        """All horses should have same default grade_wins (no popularity bias)."""
        service = PredictionService(db_session)
        analyses = await service._analyze_all_horses(test_entries, "G1")

        for entry in test_entries:
            if entry.horse_id in analyses:
                analysis = analyses[entry.horse_id]
                # 全馬同じデフォルト値（人気依存なし）
                assert analysis.grade_race_wins == 0
                assert analysis.has_actual_stats is False

    @pytest.mark.asyncio
    async def test_analyze_all_horses_keeps_odds_as_reference(self, db_session, test_race, test_entries):
        """Odds are kept as reference but not used for scoring."""
        service = PredictionService(db_session)
        analyses = await service._analyze_all_horses(test_entries, "G3")

        for entry in test_entries:
            if entry.horse_id in analyses:
                analysis = analyses[entry.horse_id]
                # オッズは参考情報として保持
                assert analysis.odds == entry.odds
                assert analysis.popularity == entry.popularity


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
    """Tests for _generate_bets method - 三連複と三連単2頭軸マルチのみ."""

    def test_trio_pivot_2_nagashi(self, db_session):
        """三連複は軸2頭流し形式."""
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
        assert bets.trio["type"] == "pivot_2_nagashi"
        assert len(bets.trio["pivots"]) == 2
        assert 1 in bets.trio["pivots"]  # 本命（スコア1位）

    def test_trifecta_multi_pivot_2(self, db_session):
        """三連単2頭軸マルチ形式."""
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

        assert bets.trifecta_multi is not None
        assert bets.trifecta_multi["type"] == "pivot_2_multi"
        assert len(bets.trifecta_multi["pivots"]) == 2
        # マルチ = 相手数 × 6パターン
        assert bets.trifecta_multi["combinations"] == len(bets.trifecta_multi["others"]) * 6

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

        # 三連複 + 三連単マルチ
        expected_total = (
            bets.trio["combinations"] * bets.trio["amount_per_ticket"]
            + bets.trifecta_multi["combinations"] * bets.trifecta_multi["amount_per_ticket"]
        )

        assert bets.total_investment == expected_total

    def test_dark_horse_as_pivot(self, db_session):
        """穴馬条件を満たす馬がいればpivotに含まれる."""
        service = PredictionService(db_session)

        # 人気8位でオッズ30倍、スコア0.20の穴馬を作成
        rankings = [
            HorsePrediction(
                rank=1, horse_id=1, horse_name="本命馬", horse_number=1,
                score=0.35, win_probability=0.25, place_probability=0.5,
                popularity=1, odds=3.0, is_dark_horse=False,
            ),
        ] + [
            HorsePrediction(
                rank=i+2, horse_id=i+2, horse_name=f"馬{i+2}", horse_number=i+2,
                score=0.2 - i*0.01, win_probability=0.1, place_probability=0.3,
                popularity=i+2, odds=float(5+i*3), is_dark_horse=False,
            )
            for i in range(6)
        ] + [
            HorsePrediction(
                rank=8, horse_id=8, horse_name="穴馬", horse_number=8,
                score=0.20, win_probability=0.08, place_probability=0.25,
                popularity=8, odds=30.0, is_dark_horse=True,
            ),
        ]
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=2, front_count=2,
        )
        analyses = {
            8: HorseAnalysis(
                horse_id=8, horse_name="穴馬", horse_number=8,
                running_style="STALKER",
                avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
                win_rate=0.1, place_rate=0.3, grade_race_wins=0,
                odds=30.0, popularity=8,
            )
        }

        bets = service._generate_bets(rankings, pace, analyses, None)

        # 穴馬8番がpivotに含まれる
        assert 8 in bets.trio["pivots"]
        assert 8 in bets.trifecta_multi["pivots"]


class TestSelectBestDarkHorse:
    """Tests for _select_best_dark_horse method."""

    def test_select_dark_horse_with_criteria(self, db_session):
        """人気8位以下、オッズ20倍以上、スコア0.18以上の穴馬を選定."""
        service = PredictionService(db_session)

        rankings = [
            HorsePrediction(
                rank=1, horse_id=1, horse_name="本命馬", horse_number=1,
                score=0.35, win_probability=0.25, place_probability=0.5,
                popularity=1, odds=3.0, is_dark_horse=False,
            ),
            HorsePrediction(
                rank=2, horse_id=2, horse_name="対抗馬", horse_number=2,
                score=0.28, win_probability=0.2, place_probability=0.45,
                popularity=2, odds=5.0, is_dark_horse=False,
            ),
            HorsePrediction(
                rank=8, horse_id=8, horse_name="穴馬", horse_number=8,
                score=0.20, win_probability=0.08, place_probability=0.25,
                popularity=8, odds=25.0, is_dark_horse=True,
            ),
        ]
        pace = PacePrediction(
            type="high", confidence=0.8, reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=2, front_count=2,
        )
        analyses = {
            8: HorseAnalysis(
                horse_id=8, horse_name="穴馬", horse_number=8,
                running_style="STALKER",
                avg_first_corner=7.0, avg_last_3f=34.0, best_last_3f=33.5,
                win_rate=0.1, place_rate=0.3, grade_race_wins=0,
                odds=25.0, popularity=8,
            )
        }

        dark_horse = service._select_best_dark_horse(rankings, analyses, pace)
        assert dark_horse.horse_number == 8

    def test_fallback_to_second_if_no_dark_horse(self, db_session):
        """穴馬条件を満たす馬がいない場合はスコア2位を返す."""
        service = PredictionService(db_session)

        # 全員人気上位
        rankings = [
            HorsePrediction(
                rank=i+1, horse_id=i+1, horse_name=f"馬{i+1}", horse_number=i+1,
                score=0.3 - i*0.02, win_probability=0.2, place_probability=0.4,
                popularity=i+1, odds=float(3+i*2), is_dark_horse=False,
            )
            for i in range(5)
        ]
        pace = PacePrediction(
            type="middle", confidence=0.6, reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1, front_count=3,
        )
        analyses = {}

        dark_horse = service._select_best_dark_horse(rankings, analyses, pace)
        # スコア2位（rank=2）を返す
        assert dark_horse.horse_number == 2


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
