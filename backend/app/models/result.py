"""Race result model."""

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class RaceResult(Base, TimestampMixin):
    """Race result table model (レース結果)."""

    __tablename__ = "race_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(Integer, ForeignKey("races.id"), nullable=False)
    horse_id: Mapped[int] = mapped_column(Integer, ForeignKey("horses.id"), nullable=False)
    jockey_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jockeys.id"), nullable=True)

    # 結果
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 着順
    time: Mapped[float | None] = mapped_column(Float, nullable=True)  # タイム（秒）
    margin: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 着差
    last_3f: Mapped[float | None] = mapped_column(Float, nullable=True)  # 上がり3F
    corner_positions: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # コーナー通過順
    prize: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 獲得賞金

    # Relationships
    race = relationship("Race", back_populates="results")
    horse = relationship("Horse", back_populates="results")
    jockey = relationship("Jockey", back_populates="results")

    def __repr__(self) -> str:
        return f"<RaceResult(id={self.id}, position={self.position})>"
