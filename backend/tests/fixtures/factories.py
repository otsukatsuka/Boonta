"""Test data factories."""

from datetime import date
from typing import Any

from app.models import Horse, Jockey, Race, RaceEntry, RaceResult, RunningStyle


def create_race_data(
    name: str = "テストレース",
    race_date: date | None = None,
    venue: str = "中山",
    course_type: str = "芝",
    distance: int = 2500,
    grade: str = "G1",
    track_condition: str = "良",
    weather: str = "晴",
    purse: int = 30000,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create race data dictionary."""
    return {
        "name": name,
        "date": race_date or date(2024, 12, 22),
        "venue": venue,
        "course_type": course_type,
        "distance": distance,
        "grade": grade,
        "track_condition": track_condition,
        "weather": weather,
        "purse": purse,
        **kwargs,
    }


def create_race(
    name: str = "テストレース",
    race_date: date | None = None,
    venue: str = "中山",
    course_type: str = "芝",
    distance: int = 2500,
    grade: str = "G1",
    track_condition: str = "良",
    weather: str = "晴",
    purse: int = 30000,
    **kwargs: Any,
) -> Race:
    """Create a Race instance."""
    return Race(
        name=name,
        date=race_date or date(2024, 12, 22),
        venue=venue,
        course_type=course_type,
        distance=distance,
        grade=grade,
        track_condition=track_condition,
        weather=weather,
        purse=purse,
        **kwargs,
    )


def create_horse(
    name: str = "テストホース",
    age: int = 4,
    sex: str = "牡",
    trainer: str = "テスト調教師",
    owner: str = "テストオーナー",
    **kwargs: Any,
) -> Horse:
    """Create a Horse instance."""
    return Horse(
        name=name,
        age=age,
        sex=sex,
        trainer=trainer,
        owner=owner,
        **kwargs,
    )


def create_jockey(
    name: str = "テスト騎手",
    win_rate: float = 0.15,
    place_rate: float = 0.35,
    venue_win_rate: float = 0.12,
    **kwargs: Any,
) -> Jockey:
    """Create a Jockey instance."""
    return Jockey(
        name=name,
        win_rate=win_rate,
        place_rate=place_rate,
        venue_win_rate=venue_win_rate,
        **kwargs,
    )


def create_entry(
    race_id: int,
    horse_id: int,
    jockey_id: int | None = None,
    horse_number: int = 1,
    post_position: int = 1,
    weight: float = 57.0,
    horse_weight: int = 480,
    horse_weight_diff: int = 0,
    odds: float = 5.0,
    popularity: int = 1,
    running_style: str = RunningStyle.FRONT.value,
    workout_evaluation: str = "B",
    **kwargs: Any,
) -> RaceEntry:
    """Create a RaceEntry instance."""
    return RaceEntry(
        race_id=race_id,
        horse_id=horse_id,
        jockey_id=jockey_id,
        horse_number=horse_number,
        post_position=post_position,
        weight=weight,
        horse_weight=horse_weight,
        horse_weight_diff=horse_weight_diff,
        odds=odds,
        popularity=popularity,
        running_style=running_style,
        workout_evaluation=workout_evaluation,
        **kwargs,
    )


def create_result(
    race_id: int,
    horse_id: int,
    jockey_id: int | None = None,
    position: int = 1,
    time: str = "2:30.5",
    margin: str = "クビ",
    last_3f: float = 34.5,
    corner_positions: str = "5-5-4-3",
    prize: int = 15000,
    **kwargs: Any,
) -> RaceResult:
    """Create a RaceResult instance."""
    return RaceResult(
        race_id=race_id,
        horse_id=horse_id,
        jockey_id=jockey_id,
        position=position,
        time=time,
        margin=margin,
        last_3f=last_3f,
        corner_positions=corner_positions,
        prize=prize,
        **kwargs,
    )


# Running style distributions for testing pace prediction
RUNNING_STYLE_DISTRIBUTIONS = {
    "high_pace": [
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
    ],
    "slow_pace": [
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
    ],
    "no_escape": [
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
    ],
    "middle_pace": [
        RunningStyle.ESCAPE.value,
        RunningStyle.ESCAPE.value,
        RunningStyle.FRONT.value,
        RunningStyle.FRONT.value,
        RunningStyle.FRONT.value,
        RunningStyle.STALKER.value,
        RunningStyle.STALKER.value,
        RunningStyle.STALKER.value,
        RunningStyle.CLOSER.value,
        RunningStyle.CLOSER.value,
    ],
}
