"""Race entry schemas."""

from pydantic import Field

from app.schemas.common import BaseSchema, RunningStyleEnum, TimestampSchema, WorkoutEvaluationEnum


class EntryBase(BaseSchema):
    """Base entry schema."""

    race_id: int = Field(..., description="レースID")
    horse_id: int = Field(..., description="馬ID")
    jockey_id: int | None = Field(None, description="騎手ID")
    post_position: int | None = Field(None, ge=1, le=8, description="枠番")
    horse_number: int | None = Field(None, ge=1, le=18, description="馬番")
    weight: float | None = Field(None, ge=40, le=70, description="斤量")
    horse_weight: int | None = Field(None, ge=300, le=600, description="馬体重")
    horse_weight_diff: int | None = Field(None, ge=-50, le=50, description="馬体重増減")
    odds: float | None = Field(None, ge=1.0, description="単勝オッズ")
    popularity: int | None = Field(None, ge=1, description="人気順")
    running_style: RunningStyleEnum | None = Field(None, description="脚質")


class EntryCreate(EntryBase):
    """Schema for creating an entry."""

    pass


class EntryUpdate(BaseSchema):
    """Schema for updating an entry."""

    jockey_id: int | None = None
    post_position: int | None = Field(None, ge=1, le=8)
    horse_number: int | None = Field(None, ge=1, le=18)
    weight: float | None = Field(None, ge=40, le=70)
    horse_weight: int | None = Field(None, ge=300, le=600)
    horse_weight_diff: int | None = Field(None, ge=-50, le=50)
    odds: float | None = Field(None, ge=1.0)
    popularity: int | None = Field(None, ge=1)
    running_style: RunningStyleEnum | None = None


class WorkoutUpdate(BaseSchema):
    """Schema for updating workout info."""

    workout_time: str | None = Field(None, max_length=20, description="追い切りタイム")
    workout_evaluation: WorkoutEvaluationEnum | None = Field(None, description="追い切り評価")
    workout_course: str | None = Field(None, max_length=50, description="追い切りコース")
    workout_memo: str | None = Field(None, description="追い切り備考")


class CommentUpdate(BaseSchema):
    """Schema for updating trainer comment."""

    trainer_comment: str | None = Field(None, description="厩舎コメント")


class EntryResponse(EntryBase, TimestampSchema):
    """Entry response schema."""

    id: int
    trainer_comment: str | None = None
    workout_time: str | None = None
    workout_evaluation: str | None = None
    workout_course: str | None = None
    workout_memo: str | None = None

    # Nested objects
    horse_name: str | None = None
    jockey_name: str | None = None


class EntryListResponse(BaseSchema):
    """Entry list response schema."""

    items: list[EntryResponse]
    total: int
