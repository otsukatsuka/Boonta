"""Race entry model."""

import enum

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class RunningStyle(str, enum.Enum):
    """Running style enum."""

    ESCAPE = "ESCAPE"  # 逃げ
    FRONT = "FRONT"  # 先行
    STALKER = "STALKER"  # 差し
    CLOSER = "CLOSER"  # 追込
    VERSATILE = "VERSATILE"  # 自在


class RaceEntry(Base, TimestampMixin):
    """Race entry table model (出走馬情報)."""

    __tablename__ = "race_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(Integer, ForeignKey("races.id"), nullable=False)
    horse_id: Mapped[int] = mapped_column(Integer, ForeignKey("horses.id"), nullable=False)
    jockey_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jockeys.id"), nullable=True)

    # 出走情報
    post_position: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 枠番
    horse_number: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 馬番
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)  # 斤量
    horse_weight: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 馬体重
    horse_weight_diff: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 馬体重増減
    odds: Mapped[float | None] = mapped_column(Float, nullable=True)  # 単勝オッズ
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 人気順

    # 脚質・追い切り情報
    running_style: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trainer_comment: Mapped[str | None] = mapped_column(Text, nullable=True)  # 厩舎コメント
    workout_time: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 追い切りタイム
    workout_evaluation: Mapped[str | None] = mapped_column(String(5), nullable=True)  # A/B/C/D
    workout_course: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 追い切りコース
    workout_memo: Mapped[str | None] = mapped_column(Text, nullable=True)  # 追い切り備考

    # Relationships
    race = relationship("Race", back_populates="entries")
    horse = relationship("Horse", back_populates="entries")
    jockey = relationship("Jockey", back_populates="entries")

    def __repr__(self) -> str:
        return f"<RaceEntry(id={self.id}, race_id={self.race_id}, horse_id={self.horse_id})>"
