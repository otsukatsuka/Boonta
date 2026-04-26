"""SQLAlchemy ORM models for Boonta.

Design rule: surrogate INTEGER PRIMARY KEY on every table; natural keys
(``race_key`` etc.) are UNIQUE-constrained, never used as PKs. Foreign keys
reference internal ids only — natural keys stay at the API boundary.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Race(Base):
    __tablename__ = "race"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_key: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    held_on: Mapped[date] = mapped_column(Date, nullable=False)
    venue_code: Mapped[str] = mapped_column(String(2), nullable=False)
    venue: Mapped[str] = mapped_column(String(8), nullable=False)
    race_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    surface: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    distance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    condition: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    weather: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    post_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    head_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pace_forecast: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    horses: Mapped[list["HorseEntry"]] = relationship(
        back_populates="race", cascade="all, delete-orphan"
    )
    payout: Mapped[Optional["HjcPayout"]] = relationship(
        back_populates="race", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (Index("ix_race_held_on", "held_on"),)


class HorseEntry(Base):
    __tablename__ = "horse_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("race.id", ondelete="CASCADE"), nullable=False
    )
    horse_number: Mapped[int] = mapped_column(Integer, nullable=False)
    waku: Mapped[Optional[int]] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    jockey: Mapped[Optional[str]] = mapped_column(String(20))
    jockey_index: Mapped[Optional[float]] = mapped_column(Float)
    weight_carried: Mapped[Optional[float]] = mapped_column(Float)
    running_style: Mapped[Optional[int]] = mapped_column(Integer)  # 1-4
    idm: Mapped[Optional[float]] = mapped_column(Float)
    mid_position: Mapped[Optional[int]] = mapped_column(Integer)
    late3f_position: Mapped[Optional[int]] = mapped_column(Integer)
    goal_position: Mapped[Optional[int]] = mapped_column(Integer)
    goal_io: Mapped[Optional[int]] = mapped_column(Integer)
    odds: Mapped[Optional[float]] = mapped_column(Float)
    fukusho_odds: Mapped[Optional[float]] = mapped_column(Float)
    popularity: Mapped[Optional[int]] = mapped_column(Integer)
    gate_miss_rate: Mapped[Optional[float]] = mapped_column(Float)
    upset_index: Mapped[Optional[int]] = mapped_column(Integer)

    race: Mapped[Race] = relationship(back_populates="horses")
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="horse_entry", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("race_id", "horse_number", name="uq_horse_entry_race_horse"),
        Index("ix_horse_entry_race", "race_id"),
    )


class Prediction(Base):
    __tablename__ = "prediction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    horse_entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("horse_entry.id", ondelete="CASCADE"), nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prob: Mapped[float] = mapped_column(Float, nullable=False)
    ev_tan: Mapped[Optional[float]] = mapped_column(Float)
    ev_fuku: Mapped[Optional[float]] = mapped_column(Float)
    predicted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Phase 2: lambdarank-derived probabilities (filled when --model-type=both)
    prob_win: Mapped[Optional[float]] = mapped_column(Float)
    prob_top2: Mapped[Optional[float]] = mapped_column(Float)
    prob_top3: Mapped[Optional[float]] = mapped_column(Float)
    lambdarank_score: Mapped[Optional[float]] = mapped_column(Float)

    horse_entry: Mapped[HorseEntry] = relationship(back_populates="predictions")

    __table_args__ = (
        UniqueConstraint(
            "horse_entry_id", "model_version", name="uq_prediction_horse_model"
        ),
    )


class HjcPayout(Base):
    __tablename__ = "hjc_payout"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("race.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    raw: Mapped[dict] = mapped_column(JSON, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    race: Mapped[Race] = relationship(back_populates="payout")


class RaceOdds(Base):
    """Pre-race combination odds (OW/OU/OT). One row per race; bet types
    stored as JSON dicts so all of wide/umatan/sanrenpuku live together."""
    __tablename__ = "race_odds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("race.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    head_count: Mapped[Optional[int]] = mapped_column(Integer)
    wide: Mapped[Optional[dict]] = mapped_column(JSON)        # {"01-02": 5.5, ...}
    umatan: Mapped[Optional[dict]] = mapped_column(JSON)      # ordered pair keys
    sanrenpuku: Mapped[Optional[dict]] = mapped_column(JSON)  # sorted triplet keys
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CybRecord(Base):
    """Per-horse training analysis (CYB). One row per (race, horse)."""
    __tablename__ = "cyb_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    horse_entry_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("horse_entry.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    finish_index: Mapped[Optional[int]] = mapped_column(Integer)
    chase_index: Mapped[Optional[int]] = mapped_column(Integer)
    training_eval: Mapped[Optional[str]] = mapped_column(String(2))
    raw: Mapped[dict] = mapped_column(JSON, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class KkaRecord(Base):
    """Extended past-race summary (KKA). One row per (race, horse)."""
    __tablename__ = "kka_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    horse_entry_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("horse_entry.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    raw: Mapped[dict] = mapped_column(JSON, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class BacktestRun(Base):
    __tablename__ = "backtest_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy: Mapped[str] = mapped_column(String(40), nullable=False)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    ev_threshold: Mapped[Optional[float]] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    races: Mapped[Optional[int]] = mapped_column(Integer)
    bet_races: Mapped[Optional[int]] = mapped_column(Integer)
    invested: Mapped[Optional[int]] = mapped_column(Integer)
    returned: Mapped[Optional[int]] = mapped_column(Integer)
    hits: Mapped[Optional[int]] = mapped_column(Integer)
    roi: Mapped[Optional[float]] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    details: Mapped[list["BacktestDetail"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    sensitivity: Mapped[list["BacktestSensitivity"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "strategy",
            "date_from",
            "date_to",
            "ev_threshold",
            "model_version",
            name="uq_backtest_run_key",
        ),
    )


class BacktestDetail(Base):
    __tablename__ = "backtest_detail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("backtest_run.id", ondelete="CASCADE"), nullable=False
    )
    race_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("race.id", ondelete="CASCADE"), nullable=False
    )
    held_on: Mapped[date] = mapped_column(Date, nullable=False)
    bets: Mapped[Optional[int]] = mapped_column(Integer)
    return_amount: Mapped[Optional[int]] = mapped_column(Integer)
    hit: Mapped[Optional[int]] = mapped_column(Integer)

    run: Mapped[BacktestRun] = relationship(back_populates="details")

    __table_args__ = (
        UniqueConstraint("run_id", "race_id", name="uq_backtest_detail_run_race"),
        Index("ix_backtest_detail_run_held", "run_id", "held_on"),
    )


class BacktestSensitivity(Base):
    __tablename__ = "backtest_sensitivity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("backtest_run.id", ondelete="CASCADE"), nullable=False
    )
    ev_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    bet_races: Mapped[Optional[int]] = mapped_column(Integer)
    hits: Mapped[Optional[int]] = mapped_column(Integer)
    roi: Mapped[Optional[float]] = mapped_column(Float)

    run: Mapped[BacktestRun] = relationship(back_populates="sensitivity")

    __table_args__ = (
        UniqueConstraint("run_id", "ev_threshold", name="uq_sensitivity_run_thr"),
    )


class TrainingRun(Base):
    __tablename__ = "training_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    preset: Mapped[str] = mapped_column(String(32), nullable=False)
    logloss: Mapped[Optional[float]] = mapped_column(Float)
    auc: Mapped[Optional[float]] = mapped_column(Float)
    brier: Mapped[Optional[float]] = mapped_column(Float)
    hit_at_3: Mapped[Optional[float]] = mapped_column(Float)
    ece: Mapped[Optional[float]] = mapped_column(Float)
    train_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    num_samples: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DEPLOYED")
    leaderboard_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_training_run_trained_at", "trained_at"),
        Index("ix_training_run_status", "status"),
    )
