"""Horse model."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Horse(Base, TimestampMixin):
    """Horse table model."""

    __tablename__ = "horses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(5), nullable=True)  # 牡/牝/セ
    trainer: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    entries = relationship("RaceEntry", back_populates="horse")
    results = relationship("RaceResult", back_populates="horse")

    def __repr__(self) -> str:
        return f"<Horse(id={self.id}, name='{self.name}')>"
