"""Prediction model."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Prediction(Base, TimestampMixin):
    """Prediction table model."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(Integer, ForeignKey("races.id"), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    prediction_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # 予測結果JSON
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 予測信頼度
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)  # 予測根拠

    # Relationships
    race = relationship("Race", back_populates="predictions")

    def __repr__(self) -> str:
        return f"<Prediction(id={self.id}, race_id={self.race_id})>"
