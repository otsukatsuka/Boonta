"""Pace prediction logic."""

from __future__ import annotations

from dataclasses import dataclass

# 競馬場特性
# front_advantage: 前有利度（正=前有利、負=差し有利）
# shape: コース形状（compact=小回り、medium=中程度、large=大回り）
# straight: 直線距離（m）
# has_uphill: 急坂の有無
VENUE_CHARACTERISTICS: dict[str, dict] = {
    "中山": {
        "front_advantage": 0.15,
        "shape": "compact",
        "straight": 310,
        "has_uphill": True,
        "description": "急坂小回り、前有利",
    },
    "東京": {
        "front_advantage": -0.10,
        "shape": "large",
        "straight": 525,
        "has_uphill": False,
        "description": "長い直線、差し有利",
    },
    "京都": {
        "front_advantage": -0.05,
        "shape": "large",
        "straight": 404,
        "has_uphill": False,
        "description": "平坦、末脚勝負",
    },
    "阪神": {
        "front_advantage": 0.0,
        "shape": "medium",
        "straight": 473,
        "has_uphill": True,
        "description": "バランス型",
    },
    "中京": {
        "front_advantage": 0.05,
        "shape": "medium",
        "straight": 412,
        "has_uphill": True,
        "description": "坂あり、やや前有利",
    },
    "小倉": {
        "front_advantage": 0.20,
        "shape": "compact",
        "straight": 293,
        "has_uphill": False,
        "description": "平坦小回り、前残り多い",
    },
    "新潟": {
        "front_advantage": -0.15,
        "shape": "large",
        "straight": 659,
        "has_uphill": False,
        "description": "超長い直線、追込有利",
    },
    "福島": {
        "front_advantage": 0.15,
        "shape": "compact",
        "straight": 292,
        "has_uphill": False,
        "description": "小回り、前有利",
    },
    "札幌": {
        "front_advantage": 0.15,
        "shape": "compact",
        "straight": 266,
        "has_uphill": False,
        "description": "洋芝小回り、前有利",
    },
    "函館": {
        "front_advantage": 0.20,
        "shape": "compact",
        "straight": 262,
        "has_uphill": False,
        "description": "洋芝最小回り、前残り",
    },
}

# 馬場状態の影響
# front_modifier: 前有利度への加算値（馬場悪化で前有利傾向）
TRACK_CONDITION_EFFECTS: dict[str, dict] = {
    "良": {
        "front_modifier": 0.0,
        "description": "標準",
    },
    "稍重": {
        "front_modifier": 0.05,
        "description": "やや時計かかる、やや前有利",
    },
    "重": {
        "front_modifier": 0.10,
        "description": "パワー必要、前残り傾向",
    },
    "不良": {
        "front_modifier": 0.15,
        "description": "消耗戦、先行有利",
    },
}


@dataclass
class PaceResult:
    """Result of pace prediction."""

    pace_type: str  # slow, middle, high
    confidence: float
    reason: str
    advantageous_styles: list[str]
    escape_count: int
    front_count: int
    stalker_count: int
    closer_count: int
    # 新規追加
    venue_adjustment: float = 0.0  # 競馬場による前有利度調整
    track_condition_adjustment: float = 0.0  # 馬場状態による調整
    venue_description: str = ""  # 競馬場特性の説明


def predict_pace(
    running_styles: list[str | None],
    distance: int = 2000,
    course_type: str = "芝",
    venue: str | None = None,
    track_condition: str | None = None,
    escape_popularities: list[int] | None = None,
) -> PaceResult:
    """
    Predict race pace based on running styles of entries.

    Args:
        running_styles: List of running styles for each entry
        distance: Race distance in meters
        course_type: Course type (芝/ダート)
        venue: Venue name (中山, 東京, etc.)
        track_condition: Track condition (良/稍重/重/不良)
        escape_popularities: List of popularity ranks for escape horses (for quality evaluation)

    Returns:
        PaceResult with pace prediction
    """
    # Count running styles
    escape_count = sum(1 for s in running_styles if s == "ESCAPE")
    front_count = sum(1 for s in running_styles if s == "FRONT")
    stalker_count = sum(1 for s in running_styles if s == "STALKER")
    closer_count = sum(1 for s in running_styles if s == "CLOSER")

    # Get venue and track condition adjustments
    venue_char = VENUE_CHARACTERISTICS.get(venue or "", {})
    venue_adjustment = venue_char.get("front_advantage", 0.0)
    venue_description = venue_char.get("description", "")
    venue_shape = venue_char.get("shape", "medium")

    track_effect = TRACK_CONDITION_EFFECTS.get(track_condition or "良", {})
    track_adjustment = track_effect.get("front_modifier", 0.0)

    # Total front advantage
    total_front_advantage = venue_adjustment + track_adjustment

    # Evaluate escape horse quality (if popularities provided)
    pace_control_factor = 1.0
    escape_quality_note = ""
    if escape_popularities and escape_count > 0:
        avg_popularity = sum(escape_popularities) / len(escape_popularities)
        has_strong_escape = any(p <= 3 for p in escape_popularities)

        if has_strong_escape:
            # Strong escape horse tends to control pace = slower
            pace_control_factor = 0.85
            escape_quality_note = "人気馬の逃げでペースは落ち着く可能性"
        elif avg_popularity >= 8:
            # Weak escape horses tend to overrace = faster
            pace_control_factor = 1.15
            escape_quality_note = "人気薄の逃げ馬で暴走の可能性"

    # Determine base pace
    if escape_count >= 3:
        pace_type = "high"
        confidence = 0.85
        reason = f"逃げ馬が{escape_count}頭と多く、激しい先行争いが予想される"
        advantageous = ["STALKER", "CLOSER"]

    elif escape_count >= 2:
        pace_type = "high"
        confidence = 0.7
        reason = f"逃げ馬{escape_count}頭による先行争いでハイペースが予想される"
        advantageous = ["STALKER", "CLOSER"]

    elif escape_count == 0:
        pace_type = "slow"
        confidence = 0.8
        reason = "逃げ馬不在でスローペース確実"
        advantageous = ["FRONT", "STALKER"]

    elif escape_count == 1 and front_count <= 2:
        pace_type = "slow"
        confidence = 0.75
        reason = f"逃げ馬1頭、先行馬も{front_count}頭と少なくスローペース濃厚"
        advantageous = ["ESCAPE", "FRONT"]

    elif escape_count == 1 and front_count >= 5:
        pace_type = "middle"
        confidence = 0.6
        reason = f"逃げ馬は1頭だが先行馬{front_count}頭で平均ペース"
        advantageous = ["FRONT", "STALKER"]

    else:
        pace_type = "middle"
        confidence = 0.5
        reason = "平均的なペースが予想される"
        advantageous = ["FRONT", "STALKER"]

    # Apply escape horse quality adjustment
    if pace_control_factor != 1.0:
        if pace_type == "high" and pace_control_factor < 1.0:
            confidence -= 0.1
            reason += f"（ただし{escape_quality_note}）"
        elif pace_type == "slow" and pace_control_factor > 1.0:
            confidence -= 0.1
            reason += f"（{escape_quality_note}）"

    # Distance adjustments
    if distance >= 2400:
        if pace_type == "high":
            confidence -= 0.1
            reason += "（長距離戦で緩む可能性あり）"
    elif distance <= 1400:
        if pace_type == "slow":
            confidence -= 0.1
            reason += "（短距離戦でペース上がる可能性あり）"

    # Course type adjustments
    if course_type == "ダート":
        if "ESCAPE" not in advantageous and "FRONT" not in advantageous:
            advantageous.insert(0, "FRONT")

    # Venue adjustments - modify advantageous styles based on front advantage
    if total_front_advantage >= 0.15:
        # Very front-favoring venue (中山, 小倉, 函館, etc.)
        if pace_type == "slow":
            # Slow pace at front-favoring venue = even more front advantage
            if "ESCAPE" not in advantageous:
                advantageous.insert(0, "ESCAPE")
            reason += f"（{venue or ''}は前残り傾向）"
        confidence += 0.05  # More predictable at these venues

    elif total_front_advantage <= -0.10:
        # Closer-favoring venue (東京, 新潟, etc.)
        if pace_type == "high":
            # High pace at long straight = closers have bigger advantage
            if "CLOSER" not in advantageous:
                advantageous.append("CLOSER")
            reason += f"（{venue or ''}は長い直線で差し有利）"
        confidence += 0.05

    # Track condition note
    if track_adjustment >= 0.10:
        reason += f"（{track_condition}馬場で前残り警戒）"

    return PaceResult(
        pace_type=pace_type,
        confidence=max(0.3, min(1.0, confidence)),
        reason=reason,
        advantageous_styles=advantageous,
        escape_count=escape_count,
        front_count=front_count,
        stalker_count=stalker_count,
        closer_count=closer_count,
        venue_adjustment=venue_adjustment,
        track_condition_adjustment=track_adjustment,
        venue_description=venue_description,
    )


def get_pace_advantage_score(
    running_style: str | None,
    pace_result: PaceResult,
) -> float:
    """
    Calculate advantage score based on running style and predicted pace.

    Args:
        running_style: Horse's running style
        pace_result: Predicted pace result

    Returns:
        Advantage score (1.0 = neutral, >1.0 = advantageous, <1.0 = disadvantageous)
    """
    if not running_style:
        return 1.0

    advantageous = pace_result.advantageous_styles

    if running_style in advantageous:
        # Position in advantage list matters
        position = advantageous.index(running_style)
        return 1.2 - (position * 0.05)  # 1.2, 1.15, 1.10, 1.05

    # Not advantageous
    if pace_result.pace_type == "high":
        if running_style in ["ESCAPE", "FRONT"]:
            return 0.85  # Front runners struggle in high pace
        return 1.0

    elif pace_result.pace_type == "slow":
        if running_style in ["STALKER", "CLOSER"]:
            return 0.85  # Back runners struggle in slow pace
        return 1.0

    return 1.0


def calculate_post_position_effect(
    post_position: int,
    running_style: str | None,
    venue: str | None = None,
    total_horses: int = 16,
) -> float:
    """
    Calculate the effect of post position on a horse's chances.

    Args:
        post_position: Post position (枠番, 1-8)
        running_style: Horse's running style
        venue: Venue name
        total_horses: Total number of horses in the race

    Returns:
        Adjustment factor (1.0 = neutral, >1.0 = advantageous, <1.0 = disadvantageous)
    """
    if not running_style or post_position is None:
        return 1.0

    venue_char = VENUE_CHARACTERISTICS.get(venue or "", {})
    shape = venue_char.get("shape", "medium")

    # Determine if inner or outer post
    is_outer = post_position >= 6  # 6-8枠は外
    is_inner = post_position <= 3  # 1-3枠は内

    adjustment = 1.0

    # Escape horses and post position
    if running_style == "ESCAPE":
        if is_outer:
            # Outer post escape horses have distance disadvantage
            adjustment *= 0.90
            if shape == "compact":
                # Even worse at small tracks (中山, 小倉, etc.)
                adjustment *= 0.95
        elif is_inner:
            # Inner post escape horses have advantage
            adjustment *= 1.05

    # Front runners
    elif running_style == "FRONT":
        if is_outer and shape == "compact":
            adjustment *= 0.95  # Slight disadvantage at small tracks

    # Stalkers and closers
    elif running_style in ["STALKER", "CLOSER"]:
        if shape == "compact":
            # At small tracks, inner post is better for these styles
            if is_inner:
                adjustment *= 1.05
            elif is_outer:
                adjustment *= 0.95
        elif shape == "large":
            # At large tracks, outer post is less of a disadvantage
            adjustment *= 1.0  # Neutral

    return adjustment
