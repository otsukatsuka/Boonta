"""Pace prediction logic."""

from dataclasses import dataclass


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


def predict_pace(
    running_styles: list[str | None],
    distance: int = 2000,
    course_type: str = "芝",
) -> PaceResult:
    """
    Predict race pace based on running styles of entries.

    Args:
        running_styles: List of running styles for each entry
        distance: Race distance in meters
        course_type: Course type (芝/ダート)

    Returns:
        PaceResult with pace prediction
    """
    # Count running styles
    escape_count = sum(1 for s in running_styles if s == "ESCAPE")
    front_count = sum(1 for s in running_styles if s == "FRONT")
    stalker_count = sum(1 for s in running_styles if s == "STALKER")
    closer_count = sum(1 for s in running_styles if s == "CLOSER")

    total_count = len([s for s in running_styles if s])

    # Determine pace
    if escape_count >= 3:
        # Many escape horses = definite high pace
        pace_type = "high"
        confidence = 0.85
        reason = f"逃げ馬が{escape_count}頭と多く、激しい先行争いが予想される"
        advantageous = ["STALKER", "CLOSER"]

    elif escape_count >= 2:
        # Two escape horses = likely high pace
        pace_type = "high"
        confidence = 0.7
        reason = f"逃げ馬{escape_count}頭による先行争いでハイペースが予想される"
        advantageous = ["STALKER", "CLOSER"]

    elif escape_count == 0:
        # No escape horses = very slow pace
        pace_type = "slow"
        confidence = 0.8
        reason = "逃げ馬不在でスローペース確実"
        advantageous = ["FRONT", "STALKER"]

    elif escape_count == 1 and front_count <= 2:
        # Single escape with few front runners = slow pace
        pace_type = "slow"
        confidence = 0.75
        reason = f"逃げ馬1頭、先行馬も{front_count}頭と少なくスローペース濃厚"
        advantageous = ["ESCAPE", "FRONT"]

    elif escape_count == 1 and front_count >= 5:
        # Single escape but many front runners = middle to high
        pace_type = "middle"
        confidence = 0.6
        reason = f"逃げ馬は1頭だが先行馬{front_count}頭で平均ペース"
        advantageous = ["FRONT", "STALKER"]

    else:
        # Default to middle pace
        pace_type = "middle"
        confidence = 0.5
        reason = "平均的なペースが予想される"
        advantageous = ["FRONT", "STALKER"]

    # Distance adjustments
    if distance >= 2400:
        # Long distance tends to be slower
        if pace_type == "high":
            confidence -= 0.1
            reason += "（長距離戦で緩む可能性あり）"
    elif distance <= 1400:
        # Short distance tends to be faster
        if pace_type == "slow":
            confidence -= 0.1
            reason += "（短距離戦でペース上がる可能性あり）"

    # Course type adjustments
    if course_type == "ダート":
        # Dirt races tend to favor front runners more
        if "ESCAPE" not in advantageous and "FRONT" not in advantageous:
            advantageous.insert(0, "FRONT")

    return PaceResult(
        pace_type=pace_type,
        confidence=max(0.3, min(1.0, confidence)),
        reason=reason,
        advantageous_styles=advantageous,
        escape_count=escape_count,
        front_count=front_count,
        stalker_count=stalker_count,
        closer_count=closer_count,
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
