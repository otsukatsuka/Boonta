"""Prediction schemas."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class HorsePrediction(BaseSchema):
    """Individual horse prediction."""

    rank: int = Field(..., ge=1, description="予測順位")
    horse_id: int = Field(..., description="馬ID")
    horse_name: str = Field(..., description="馬名")
    horse_number: int = Field(..., description="馬番")
    score: float = Field(..., ge=0, le=1, description="予測スコア")
    win_probability: float = Field(..., ge=0, le=1, description="勝率予測")
    place_probability: float = Field(..., ge=0, le=1, description="複勝率予測")
    popularity: int | None = Field(None, ge=1, description="人気順")
    odds: float | None = Field(None, ge=1.0, description="単勝オッズ")
    is_dark_horse: bool = Field(False, description="穴馬フラグ")
    dark_horse_reason: str | None = Field(None, description="穴馬理由")


class PacePrediction(BaseSchema):
    """Pace prediction."""

    type: str = Field(..., description="ペースタイプ (slow/middle/high)")
    confidence: float = Field(..., ge=0, le=1, description="信頼度")
    reason: str = Field(..., description="理由")
    advantageous_styles: list[str] = Field(default_factory=list, description="有利な脚質")
    escape_count: int = Field(0, ge=0, description="逃げ馬数")
    front_count: int = Field(0, ge=0, description="先行馬数")


class BetRecommendation(BaseSchema):
    """Bet recommendation - 三連複と三連単2頭軸マルチのみ."""

    trio: dict[str, Any] | None = Field(None, description="三連複（軸2頭流し）")
    trifecta_multi: dict[str, Any] | None = Field(None, description="三連単2頭軸マルチ")
    total_investment: int = Field(0, ge=0, description="合計投資額")
    note: str | None = Field(None, description="備考")


class PredictionCreate(BaseSchema):
    """Schema for creating a prediction."""

    race_id: int = Field(..., description="レースID")


class PredictionResponse(BaseSchema):
    """Prediction response schema."""

    race_id: int
    model_version: str
    predicted_at: datetime
    rankings: list[HorsePrediction]
    pace_prediction: PacePrediction | None = None
    recommended_bets: BetRecommendation | None = None
    confidence_score: float | None = None
    reasoning: str | None = None


class PredictionHistoryResponse(TimestampSchema):
    """Prediction history response."""

    id: int
    race_id: int
    model_version: str
    predicted_at: datetime
    confidence_score: float | None = None


class PredictionHistoryListResponse(BaseSchema):
    """Prediction history list response."""

    items: list[PredictionHistoryResponse]
    total: int


class ModelStatusResponse(BaseSchema):
    """Model status response."""

    model_version: str
    is_trained: bool
    last_trained_at: datetime | None = None
    training_data_count: int = 0
    metrics: dict[str, float] | None = None


class FeatureImportanceResponse(BaseSchema):
    """Feature importance response."""

    features: list[dict[str, Any]]
