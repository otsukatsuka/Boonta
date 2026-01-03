"""Tests for pace prediction logic."""

import pytest

from app.ml.pace import (
    TRACK_CONDITION_EFFECTS,
    VENUE_CHARACTERISTICS,
    PaceResult,
    calculate_post_position_effect,
    get_pace_advantage_score,
    predict_pace,
)
from app.models import RunningStyle


class TestVenueCharacteristics:
    """Tests for VENUE_CHARACTERISTICS dictionary."""

    def test_all_10_venues_defined(self):
        """Verify all 10 major Japanese venues are defined."""
        expected_venues = [
            "中山", "東京", "京都", "阪神", "中京",
            "小倉", "新潟", "福島", "札幌", "函館",
        ]
        for venue in expected_venues:
            assert venue in VENUE_CHARACTERISTICS, f"Missing venue: {venue}"

    def test_front_advantage_values(self):
        """Verify front advantage values for key venues."""
        # Front-favoring venues
        assert VENUE_CHARACTERISTICS["中山"]["front_advantage"] == 0.15
        assert VENUE_CHARACTERISTICS["小倉"]["front_advantage"] == 0.20
        assert VENUE_CHARACTERISTICS["函館"]["front_advantage"] == 0.20
        assert VENUE_CHARACTERISTICS["福島"]["front_advantage"] == 0.15
        assert VENUE_CHARACTERISTICS["札幌"]["front_advantage"] == 0.15

        # Closer-favoring venues
        assert VENUE_CHARACTERISTICS["東京"]["front_advantage"] == -0.10
        assert VENUE_CHARACTERISTICS["新潟"]["front_advantage"] == -0.15
        assert VENUE_CHARACTERISTICS["京都"]["front_advantage"] == -0.05

        # Neutral venues
        assert VENUE_CHARACTERISTICS["阪神"]["front_advantage"] == 0.0
        assert VENUE_CHARACTERISTICS["中京"]["front_advantage"] == 0.05

    def test_venue_shapes(self):
        """Verify venue shape classifications."""
        compact_venues = ["中山", "小倉", "福島", "札幌", "函館"]
        large_venues = ["東京", "京都", "新潟"]
        medium_venues = ["阪神", "中京"]

        for venue in compact_venues:
            assert VENUE_CHARACTERISTICS[venue]["shape"] == "compact"

        for venue in large_venues:
            assert VENUE_CHARACTERISTICS[venue]["shape"] == "large"

        for venue in medium_venues:
            assert VENUE_CHARACTERISTICS[venue]["shape"] == "medium"

    def test_straight_distances(self):
        """Verify straight distances for key venues."""
        assert VENUE_CHARACTERISTICS["東京"]["straight"] == 525
        assert VENUE_CHARACTERISTICS["新潟"]["straight"] == 659
        assert VENUE_CHARACTERISTICS["函館"]["straight"] == 262
        assert VENUE_CHARACTERISTICS["中山"]["straight"] == 310

    def test_uphill_presence(self):
        """Verify uphill presence for key venues."""
        assert VENUE_CHARACTERISTICS["中山"]["has_uphill"] is True
        assert VENUE_CHARACTERISTICS["阪神"]["has_uphill"] is True
        assert VENUE_CHARACTERISTICS["中京"]["has_uphill"] is True

        assert VENUE_CHARACTERISTICS["東京"]["has_uphill"] is False
        assert VENUE_CHARACTERISTICS["京都"]["has_uphill"] is False
        assert VENUE_CHARACTERISTICS["新潟"]["has_uphill"] is False


class TestTrackConditionEffects:
    """Tests for TRACK_CONDITION_EFFECTS dictionary."""

    def test_all_conditions_defined(self):
        """Verify all 4 track conditions are defined."""
        expected_conditions = ["良", "稍重", "重", "不良"]
        for condition in expected_conditions:
            assert condition in TRACK_CONDITION_EFFECTS, f"Missing condition: {condition}"

    def test_front_modifiers(self):
        """Verify front modifiers for each condition."""
        assert TRACK_CONDITION_EFFECTS["良"]["front_modifier"] == 0.0
        assert TRACK_CONDITION_EFFECTS["稍重"]["front_modifier"] == 0.05
        assert TRACK_CONDITION_EFFECTS["重"]["front_modifier"] == 0.10
        assert TRACK_CONDITION_EFFECTS["不良"]["front_modifier"] == 0.15

    def test_descriptions_present(self):
        """Verify all conditions have descriptions."""
        for condition, effect in TRACK_CONDITION_EFFECTS.items():
            assert "description" in effect, f"Missing description for {condition}"
            assert len(effect["description"]) > 0


class TestPredictPace:
    """Tests for predict_pace function."""

    def test_3_escape_horses_high_pace(self, high_pace_styles):
        """3+ ESCAPE horses should result in high pace with high confidence."""
        result = predict_pace(high_pace_styles)

        assert result.pace_type == "high"
        assert result.confidence >= 0.80
        assert result.escape_count == 3
        assert "STALKER" in result.advantageous_styles
        assert "CLOSER" in result.advantageous_styles

    def test_2_escape_horses_high_pace(self):
        """2 ESCAPE horses should result in high pace."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
            RunningStyle.STALKER.value,
            RunningStyle.CLOSER.value,
            RunningStyle.CLOSER.value,
        ]
        result = predict_pace(styles)

        assert result.pace_type == "high"
        assert result.confidence >= 0.65
        assert result.escape_count == 2

    def test_0_escape_horses_slow_pace(self, no_escape_styles):
        """0 ESCAPE horses should result in slow pace."""
        result = predict_pace(no_escape_styles)

        assert result.pace_type == "slow"
        assert result.confidence >= 0.75
        assert result.escape_count == 0
        assert "FRONT" in result.advantageous_styles
        assert "STALKER" in result.advantageous_styles

    def test_1_escape_few_front_slow_pace(self, slow_pace_styles):
        """1 ESCAPE with few FRONT horses should result in slow pace."""
        result = predict_pace(slow_pace_styles)

        assert result.pace_type == "slow"
        assert result.escape_count == 1
        assert result.front_count <= 2
        assert "ESCAPE" in result.advantageous_styles
        assert "FRONT" in result.advantageous_styles

    def test_1_escape_many_front_middle_pace(self):
        """1 ESCAPE with many FRONT horses should result in middle pace."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.FRONT.value,
            RunningStyle.FRONT.value,
            RunningStyle.FRONT.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
            RunningStyle.STALKER.value,
            RunningStyle.CLOSER.value,
            RunningStyle.CLOSER.value,
        ]
        result = predict_pace(styles)

        assert result.pace_type == "middle"
        assert result.escape_count == 1
        assert result.front_count == 5

    def test_escape_quality_strong_horse(self):
        """Strong escape horse (high popularity) should reduce pace."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
        ]
        # Popular escape horses (1, 2, 3)
        result = predict_pace(styles, escape_popularities=[1, 2, 3])

        assert result.pace_type == "high"
        # Confidence should be reduced due to pace control
        assert result.confidence < 0.85
        assert "人気馬" in result.reason

    def test_escape_quality_weak_horse(self):
        """Weak escape horses should increase pace likelihood."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
            RunningStyle.STALKER.value,
        ]
        # Unpopular escape horse
        result = predict_pace(styles, escape_popularities=[10])

        assert "人気薄" in result.reason

    def test_long_distance_adjustment(self):
        """Long distance (>=2400m) should reduce high pace confidence."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
        ]
        result = predict_pace(styles, distance=2500)

        assert result.pace_type == "high"
        assert "長距離" in result.reason
        # Confidence should be reduced
        assert result.confidence < 0.85

    def test_short_distance_adjustment(self):
        """Short distance (<=1400m) should reduce slow pace confidence."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
            RunningStyle.STALKER.value,
        ]
        result = predict_pace(styles, distance=1200)

        # Should be slow but with reduced confidence
        assert "短距離" in result.reason

    def test_dirt_course_front_advantage(self):
        """Dirt course should add FRONT to advantageous if not present."""
        # High pace scenario where FRONT wouldn't normally be advantageous
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.STALKER.value,
            RunningStyle.CLOSER.value,
        ]
        result = predict_pace(styles, course_type="ダート")

        # FRONT should be added for dirt
        assert "FRONT" in result.advantageous_styles

    def test_venue_adjustment_nakayama(self):
        """中山 (front-favoring venue) should add ESCAPE to slow pace advantage."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
            RunningStyle.CLOSER.value,
        ]
        result = predict_pace(styles, venue="中山")

        assert result.venue_adjustment == 0.15
        assert result.venue_description == "急坂小回り、前有利"
        # Slow pace at front-favoring venue
        if result.pace_type == "slow":
            assert "ESCAPE" in result.advantageous_styles
            assert "中山" in result.reason

    def test_venue_adjustment_tokyo(self):
        """東京 (closer-favoring venue) should add CLOSER to high pace advantage."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
        ]
        result = predict_pace(styles, venue="東京")

        assert result.venue_adjustment == -0.10
        assert result.venue_description == "長い直線、差し有利"
        assert "CLOSER" in result.advantageous_styles
        assert "東京" in result.reason

    def test_track_condition_effect(self):
        """Heavy track should add to front advantage."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
        ]
        result = predict_pace(styles, track_condition="重")

        assert result.track_condition_adjustment == 0.10
        assert "重馬場" in result.reason or "重" in result.reason

    def test_unknown_venue_defaults(self):
        """Unknown venue should use default values."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
        ]
        result = predict_pace(styles, venue="Unknown")

        assert result.venue_adjustment == 0.0
        assert result.venue_description == ""

    def test_counts_correct(self):
        """Verify running style counts are correct."""
        styles = [
            RunningStyle.ESCAPE.value,
            RunningStyle.ESCAPE.value,
            RunningStyle.FRONT.value,
            RunningStyle.FRONT.value,
            RunningStyle.FRONT.value,
            RunningStyle.STALKER.value,
            RunningStyle.STALKER.value,
            RunningStyle.STALKER.value,
            RunningStyle.STALKER.value,
            RunningStyle.CLOSER.value,
            RunningStyle.CLOSER.value,
            RunningStyle.CLOSER.value,
        ]
        result = predict_pace(styles)

        assert result.escape_count == 2
        assert result.front_count == 3
        assert result.stalker_count == 4
        assert result.closer_count == 3

    def test_confidence_bounds(self):
        """Confidence should be bounded between 0.3 and 1.0."""
        # Test with extreme adjustments
        styles = [RunningStyle.ESCAPE.value] * 5
        result = predict_pace(
            styles,
            distance=3000,
            venue="東京",
            escape_popularities=[1, 1, 1, 1, 1],
        )

        assert 0.3 <= result.confidence <= 1.0


class TestGetPaceAdvantageScore:
    """Tests for get_pace_advantage_score function."""

    def test_first_advantage_position(self):
        """First position in advantage list should get highest score."""
        pace_result = PaceResult(
            pace_type="high",
            confidence=0.8,
            reason="Test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3,
            front_count=2,
            stalker_count=3,
            closer_count=2,
        )
        score = get_pace_advantage_score("STALKER", pace_result)
        assert score == 1.2  # First position

    def test_second_advantage_position(self):
        """Second position should get slightly lower score."""
        pace_result = PaceResult(
            pace_type="high",
            confidence=0.8,
            reason="Test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3,
            front_count=2,
            stalker_count=3,
            closer_count=2,
        )
        score = get_pace_advantage_score("CLOSER", pace_result)
        assert score == 1.15  # Second position

    def test_not_advantageous_high_pace_escape(self):
        """ESCAPE in high pace should get disadvantage."""
        pace_result = PaceResult(
            pace_type="high",
            confidence=0.8,
            reason="Test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3,
            front_count=2,
            stalker_count=3,
            closer_count=2,
        )
        score = get_pace_advantage_score("ESCAPE", pace_result)
        assert score == 0.85

    def test_not_advantageous_high_pace_front(self):
        """FRONT in high pace should get disadvantage."""
        pace_result = PaceResult(
            pace_type="high",
            confidence=0.8,
            reason="Test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3,
            front_count=2,
            stalker_count=3,
            closer_count=2,
        )
        score = get_pace_advantage_score("FRONT", pace_result)
        assert score == 0.85

    def test_not_advantageous_slow_pace_stalker(self):
        """STALKER in slow pace (not in advantage list) should get disadvantage."""
        pace_result = PaceResult(
            pace_type="slow",
            confidence=0.8,
            reason="Test",
            advantageous_styles=["ESCAPE", "FRONT"],
            escape_count=1,
            front_count=2,
            stalker_count=3,
            closer_count=2,
        )
        score = get_pace_advantage_score("STALKER", pace_result)
        assert score == 0.85

    def test_not_advantageous_slow_pace_closer(self):
        """CLOSER in slow pace should get disadvantage."""
        pace_result = PaceResult(
            pace_type="slow",
            confidence=0.8,
            reason="Test",
            advantageous_styles=["ESCAPE", "FRONT"],
            escape_count=1,
            front_count=2,
            stalker_count=3,
            closer_count=2,
        )
        score = get_pace_advantage_score("CLOSER", pace_result)
        assert score == 0.85

    def test_neutral_style_middle_pace(self):
        """Non-advantageous style in middle pace should be neutral."""
        pace_result = PaceResult(
            pace_type="middle",
            confidence=0.6,
            reason="Test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1,
            front_count=3,
            stalker_count=3,
            closer_count=3,
        )
        score = get_pace_advantage_score("CLOSER", pace_result)
        assert score == 1.0

    def test_none_running_style(self):
        """None running style should return neutral score."""
        pace_result = PaceResult(
            pace_type="middle",
            confidence=0.6,
            reason="Test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=1,
            front_count=3,
            stalker_count=3,
            closer_count=3,
        )
        score = get_pace_advantage_score(None, pace_result)
        assert score == 1.0


class TestCalculatePostPositionEffect:
    """Tests for calculate_post_position_effect function."""

    def test_escape_outer_post_penalty(self):
        """ESCAPE at outer post (6-8) should get penalty."""
        effect = calculate_post_position_effect(
            post_position=7,
            running_style="ESCAPE",
            venue="東京",  # Large track
        )
        assert effect == 0.90

    def test_escape_outer_compact_venue_extra_penalty(self):
        """ESCAPE at outer post on compact venue should get extra penalty."""
        effect = calculate_post_position_effect(
            post_position=7,
            running_style="ESCAPE",
            venue="中山",  # Compact track
        )
        assert effect == pytest.approx(0.90 * 0.95)  # 0.855

    def test_escape_inner_post_bonus(self):
        """ESCAPE at inner post (1-3) should get bonus."""
        effect = calculate_post_position_effect(
            post_position=2,
            running_style="ESCAPE",
            venue="中山",
        )
        assert effect == 1.05

    def test_front_outer_compact_slight_disadvantage(self):
        """FRONT at outer post on compact venue should have slight disadvantage."""
        effect = calculate_post_position_effect(
            post_position=7,
            running_style="FRONT",
            venue="小倉",  # Compact
        )
        assert effect == 0.95

    def test_front_outer_large_venue_neutral(self):
        """FRONT at outer post on large venue should be neutral."""
        effect = calculate_post_position_effect(
            post_position=7,
            running_style="FRONT",
            venue="東京",  # Large
        )
        assert effect == 1.0

    def test_stalker_inner_compact_bonus(self):
        """STALKER at inner post on compact venue should get bonus."""
        effect = calculate_post_position_effect(
            post_position=2,
            running_style="STALKER",
            venue="函館",  # Compact
        )
        assert effect == 1.05

    def test_stalker_outer_compact_disadvantage(self):
        """STALKER at outer post on compact venue should get disadvantage."""
        effect = calculate_post_position_effect(
            post_position=7,
            running_style="STALKER",
            venue="中山",  # Compact
        )
        assert effect == 0.95

    def test_closer_inner_compact_bonus(self):
        """CLOSER at inner post on compact venue should get bonus."""
        effect = calculate_post_position_effect(
            post_position=1,
            running_style="CLOSER",
            venue="小倉",  # Compact
        )
        assert effect == 1.05

    def test_closer_large_venue_neutral(self):
        """CLOSER at any post on large venue should be neutral."""
        # Inner post
        effect = calculate_post_position_effect(
            post_position=2,
            running_style="CLOSER",
            venue="新潟",  # Large
        )
        assert effect == 1.0

        # Outer post
        effect = calculate_post_position_effect(
            post_position=7,
            running_style="CLOSER",
            venue="東京",  # Large
        )
        assert effect == 1.0

    def test_none_running_style_neutral(self):
        """None running style should return neutral effect."""
        effect = calculate_post_position_effect(
            post_position=5,
            running_style=None,
            venue="中山",
        )
        assert effect == 1.0

    def test_none_post_position_neutral(self):
        """None post position should return neutral effect."""
        effect = calculate_post_position_effect(
            post_position=None,
            running_style="ESCAPE",
            venue="中山",
        )
        assert effect == 1.0

    def test_unknown_venue_medium_shape(self):
        """Unknown venue should use medium shape defaults."""
        effect = calculate_post_position_effect(
            post_position=7,
            running_style="ESCAPE",
            venue="Unknown",
        )
        # Outer escape without compact venue = 0.90 (no extra penalty)
        assert effect == 0.90

    def test_middle_post_neutral(self):
        """Middle post (4-5) should generally be neutral."""
        effect = calculate_post_position_effect(
            post_position=5,
            running_style="ESCAPE",
            venue="中山",
        )
        # Post 5 is not inner (<=3) or outer (>=6), so should be neutral
        assert effect == 1.0
