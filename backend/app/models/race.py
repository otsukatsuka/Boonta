"""Race model."""

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Race(Base, TimestampMixin):
    """Race table model."""

    __tablename__ = "races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    venue: Mapped[str] = mapped_column(String(20), nullable=False)
    course_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 芝/ダート
    distance: Mapped[int] = mapped_column(Integer, nullable=False)
    track_condition: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 良/稍重/重/不良
    weather: Mapped[str | None] = mapped_column(String(10), nullable=True)
    grade: Mapped[str] = mapped_column(String(10), nullable=False)  # G1/G2/G3/OP
    purse: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 賞金（万円）

    # Relationships
    entries = relationship("RaceEntry", back_populates="race", cascade="all, delete-orphan")
    results = relationship("RaceResult", back_populates="race", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="race", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Race(id={self.id}, name='{self.name}', date={self.date})>"
