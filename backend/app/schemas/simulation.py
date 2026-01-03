"""Simulation schemas for race visualization."""

from pydantic import Field

from app.schemas.common import BaseSchema


class HorsePosition(BaseSchema):
    """Horse position in a corner."""

    horse_number: int = Field(..., description="馬番")
    horse_name: str = Field(..., description="馬名")
    running_style: str | None = Field(None, description="脚質")
    position: int = Field(..., ge=1, description="順位")
    distance_from_leader: float = Field(0.0, ge=0, description="先頭からの距離（馬身）")


class CornerPositions(BaseSchema):
    """Positions at a specific corner."""

    corner_name: str = Field(..., description="コーナー名 (1C/2C/3C/4C/goal)")
    horses: list[HorsePosition] = Field(default_factory=list, description="各馬の位置")


class FormationHorse(BaseSchema):
    """Horse in formation diagram."""

    horse_number: int = Field(..., description="馬番")
    horse_name: str = Field(..., description="馬名")
    running_style: str | None = Field(None, description="脚質")


class FormationRow(BaseSchema):
    """A row in the start formation."""

    row_index: int = Field(..., ge=0, description="行インデックス（0=先頭）")
    row_label: str = Field(..., description="行ラベル（先頭/先行/中団/後方）")
    horses: list[FormationHorse] = Field(default_factory=list, description="この行の馬")


class StartFormation(BaseSchema):
    """Start formation diagram data."""

    rows: list[FormationRow] = Field(default_factory=list, description="行データ")
    total_horses: int = Field(0, ge=0, description="総頭数")


class ScenarioRanking(BaseSchema):
    """Horse ranking in a scenario."""

    rank: int = Field(..., ge=1, description="予想順位")
    horse_number: int = Field(..., description="馬番")
    horse_name: str = Field(..., description="馬名")
    score: float = Field(..., ge=0, le=1, description="スコア")


class ScenarioKeyHorse(BaseSchema):
    """Key horse in a scenario."""

    horse_number: int = Field(..., description="馬番")
    horse_name: str = Field(..., description="馬名")
    reason: str = Field(..., description="注目理由")


class ScenarioResult(BaseSchema):
    """Result for a pace scenario."""

    pace_type: str = Field(..., description="ペースタイプ (slow/middle/high)")
    pace_label: str = Field(..., description="ペースラベル（日本語）")
    probability: float = Field(..., ge=0, le=1, description="発生確率")
    rankings: list[ScenarioRanking] = Field(default_factory=list, description="上位5頭")
    key_horses: list[ScenarioKeyHorse] = Field(default_factory=list, description="注目馬")
    advantageous_styles: list[str] = Field(default_factory=list, description="有利な脚質")
    description: str = Field("", description="シナリオ説明")


class TrackConditionResult(BaseSchema):
    """Result for a track condition scenario."""

    track_condition: str = Field(..., description="馬場状態 (良/稍重/重/不良)")
    front_advantage: float = Field(..., description="前有利度 (0.0~0.3)")
    rankings: list[ScenarioRanking] = Field(default_factory=list, description="上位5頭")
    key_horses: list[ScenarioKeyHorse] = Field(default_factory=list, description="注目馬（この馬場で有利な馬）")
    advantageous_styles: list[str] = Field(default_factory=list, description="有利な脚質")
    description: str = Field("", description="馬場状態の説明")


class AnimationHorse(BaseSchema):
    """Horse position in animation frame."""

    horse_number: int = Field(..., description="馬番")
    horse_name: str = Field(..., description="馬名")
    running_style: str | None = Field(None, description="脚質")
    progress: float = Field(..., ge=0, le=1, description="コース進行度 (0-1)")
    lane: int = Field(..., ge=1, le=8, description="内外の位置 (1=最内)")


class AnimationFrame(BaseSchema):
    """A frame in the race animation."""

    time: float = Field(..., ge=0, le=1, description="レース進行度 (0-1)")
    horses: list[AnimationHorse] = Field(default_factory=list, description="各馬の位置")


class RaceSimulation(BaseSchema):
    """Complete race simulation data."""

    race_id: int = Field(..., description="レースID")
    race_name: str = Field("", description="レース名")
    distance: int = Field(2000, description="距離（m）")
    course_type: str = Field("芝", description="コース種別")
    venue: str | None = Field(None, description="競馬場")
    track_condition: str | None = Field(None, description="馬場状態（良/稍重/重/不良）")
    venue_description: str | None = Field(None, description="競馬場の特性説明")

    # Position chart data
    corner_positions: list[CornerPositions] = Field(
        default_factory=list, description="コーナー毎の位置取り"
    )

    # Formation diagram data
    start_formation: StartFormation = Field(
        default_factory=StartFormation, description="スタート時の隊列"
    )

    # Scenario comparison data (pace-based)
    scenarios: list[ScenarioResult] = Field(
        default_factory=list, description="ペース別シナリオ結果"
    )

    # Track condition scenarios
    track_condition_scenarios: list[TrackConditionResult] = Field(
        default_factory=list, description="馬場状態別シナリオ結果"
    )

    # Current predicted pace
    predicted_pace: str = Field("middle", description="予測ペース")

    # Animation data (optional, can be large)
    animation_frames: list[AnimationFrame] | None = Field(
        None, description="アニメーションフレーム"
    )
