"""Jockey model."""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Jockey(Base, TimestampMixin):
    """Jockey table model."""

    __tablename__ = "jockeys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    place_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    venue_win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    entries = relationship("RaceEntry", back_populates="jockey")
    results = relationship("RaceResult", back_populates="jockey")

    def __repr__(self) -> str:
        return f"<Jockey(id={self.id}, name='{self.name}')>"
