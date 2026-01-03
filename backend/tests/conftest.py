"""Shared test fixtures."""

import sys
from datetime import date
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base
from app.models import Horse, Jockey, Race, RaceEntry, RaceResult, RunningStyle

from tests.fixtures.factories import create_entry, create_horse, create_jockey, create_race


@pytest.fixture
async def db_engine():
    """Create in-memory SQLite engine for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session with transaction rollback."""
    async_session = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_race(db_session: AsyncSession) -> Race:
    """Create a sample race for testing."""
    race = create_race(
        name="有馬記念",
        race_date=date(2024, 12, 22),
        venue="中山",
        course_type="芝",
        distance=2500,
        grade="G1",
        track_condition="良",
    )
    db_session.add(race)
    await db_session.flush()
    return race


@pytest.fixture
async def test_horse(db_session: AsyncSession) -> Horse:
    """Create a sample horse for testing."""
    horse = create_horse(name="イクイノックス", age=5, sex="牡")
    db_session.add(horse)
    await db_session.flush()
    return horse


@pytest.fixture
async def test_jockey(db_session: AsyncSession) -> Jockey:
    """Create a sample jockey for testing."""
    jockey = create_jockey(
        name="C.ルメール",
        win_rate=0.20,
        place_rate=0.45,
        venue_win_rate=0.18,
    )
    db_session.add(jockey)
    await db_session.flush()
    return jockey


@pytest.fixture
async def test_horses(db_session: AsyncSession) -> list[Horse]:
    """Create 16 horses for a full race field."""
    horses = []
    horse_names = [
        "イクイノックス", "ドウデュース", "スターズオンアース", "ジャスティンパレス",
        "タイトルホルダー", "ジェラルディーナ", "ボルドグフーシュ", "ヒシイグアス",
        "エフフォーリア", "ディープボンド", "シャフリヤール", "ダノンベルーガ",
        "プログノーシス", "アスクビクターモア", "ヴェラアズール", "スルーセブンシーズ",
    ]
    for i, name in enumerate(horse_names, 1):
        horse = create_horse(name=name, age=4 + (i % 3), sex="牡" if i % 3 != 0 else "牝")
        db_session.add(horse)
        horses.append(horse)
    await db_session.flush()
    return horses


@pytest.fixture
async def test_jockeys(db_session: AsyncSession) -> list[Jockey]:
    """Create jockeys for testing."""
    jockeys = []
    jockey_data = [
        ("C.ルメール", 0.20, 0.45),
        ("武豊", 0.18, 0.40),
        ("川田将雅", 0.17, 0.42),
        ("横山武史", 0.15, 0.38),
        ("戸崎圭太", 0.14, 0.36),
        ("福永祐一", 0.16, 0.39),
        ("M.デムーロ", 0.13, 0.35),
        ("松山弘平", 0.12, 0.33),
    ]
    for name, win_rate, place_rate in jockey_data:
        jockey = create_jockey(name=name, win_rate=win_rate, place_rate=place_rate)
        db_session.add(jockey)
        jockeys.append(jockey)
    await db_session.flush()
    return jockeys


@pytest.fixture
async def test_entries(
    db_session: AsyncSession,
    test_race: Race,
    test_horses: list[Horse],
    test_jockeys: list[Jockey],
) -> list[RaceEntry]:
    """Create 16 test entries with varied running styles and odds."""
    entries = []
    running_styles = [
        RunningStyle.ESCAPE.value,  # 1
        RunningStyle.ESCAPE.value,  # 2
        RunningStyle.FRONT.value,   # 3
        RunningStyle.FRONT.value,   # 4
        RunningStyle.FRONT.value,   # 5
        RunningStyle.STALKER.value, # 6
        RunningStyle.STALKER.value, # 7
        RunningStyle.STALKER.value, # 8
        RunningStyle.STALKER.value, # 9
        RunningStyle.CLOSER.value,  # 10
        RunningStyle.CLOSER.value,  # 11
        RunningStyle.CLOSER.value,  # 12
        RunningStyle.VERSATILE.value, # 13
        RunningStyle.VERSATILE.value, # 14
        RunningStyle.VERSATILE.value, # 15
        RunningStyle.VERSATILE.value, # 16
    ]

    # Realistic odds distribution
    odds_list = [2.5, 4.0, 6.5, 8.0, 12.0, 15.0, 20.0, 25.0,
                 30.0, 40.0, 50.0, 60.0, 80.0, 100.0, 120.0, 150.0]

    for i, (horse, style, odds) in enumerate(zip(test_horses, running_styles, odds_list), 1):
        jockey = test_jockeys[i % len(test_jockeys)]
        entry = create_entry(
            race_id=test_race.id,
            horse_id=horse.id,
            jockey_id=jockey.id,
            horse_number=i,
            post_position=(i - 1) // 2 + 1,  # 1-8枠
            weight=57.0 if i <= 10 else 55.0,
            horse_weight=480 + (i * 5),
            horse_weight_diff=(-4 + i) if i <= 8 else (i - 12),
            odds=odds,
            popularity=i,
            running_style=style,
            workout_evaluation="A" if i <= 3 else ("B" if i <= 8 else "C"),
        )
        db_session.add(entry)
        entries.append(entry)

    await db_session.flush()
    return entries


@pytest.fixture
async def test_results(
    db_session: AsyncSession,
    test_race: Race,
    test_horses: list[Horse],
    test_jockeys: list[Jockey],
) -> list[RaceResult]:
    """Create race results for testing."""
    results = []
    for i, horse in enumerate(test_horses[:10], 1):
        jockey = test_jockeys[i % len(test_jockeys)]
        # time is in seconds (e.g., 150.5 = 2:30.5)
        time_seconds = 150.0 + i * 1.5
        result = RaceResult(
            race_id=test_race.id,
            horse_id=horse.id,
            jockey_id=jockey.id,
            position=i,
            time=time_seconds,
            margin="アタマ" if i <= 3 else "1/2",
            last_3f=33.5 + (i * 0.3),
            corner_positions={"corners": [i+2, i+1, i, i]},  # JSON format
            prize=30000 // i if i <= 3 else 0,
        )
        db_session.add(result)
        results.append(result)
    await db_session.flush()
    return results


@pytest.fixture
def mock_ml_predictor():
    """Mock AutoGluon predictor returning None (no model available)."""
    mock = MagicMock()
    mock.return_value = None
    return mock


# Utility fixtures for pace testing
@pytest.fixture
def high_pace_styles() -> list[str]:
    """Running styles that create a high pace scenario."""
    return [
        RunningStyle.ESCAPE.value,
        RunningStyle.ESCAPE.value,
        RunningStyle.ESCAPE.value,
        RunningStyle.FRONT.value,
        RunningStyle.FRONT.value,
        RunningStyle.STALKER.value,
        RunningStyle.STALKER.value,
        RunningStyle.STALKER.value,
        RunningStyle.CLOSER.value,
        RunningStyle.CLOSER.value,
    ]


@pytest.fixture
def slow_pace_styles() -> list[str]:
    """Running styles that create a slow pace scenario."""
    return [
        RunningStyle.ESCAPE.value,
        RunningStyle.FRONT.value,
        RunningStyle.STALKER.value,
        RunningStyle.STALKER.value,
        RunningStyle.STALKER.value,
        RunningStyle.STALKER.value,
        RunningStyle.CLOSER.value,
        RunningStyle.CLOSER.value,
        RunningStyle.CLOSER.value,
        RunningStyle.CLOSER.value,
    ]


@pytest.fixture
def no_escape_styles() -> list[str]:
    """Running styles with no escape horses."""
    return [
        RunningStyle.FRONT.value,
        RunningStyle.FRONT.value,
        RunningStyle.FRONT.value,
        RunningStyle.STALKER.value,
        RunningStyle.STALKER.value,
        RunningStyle.STALKER.value,
        RunningStyle.CLOSER.value,
        RunningStyle.CLOSER.value,
        RunningStyle.CLOSER.value,
        RunningStyle.CLOSER.value,
    ]
