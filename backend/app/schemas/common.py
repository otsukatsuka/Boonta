"""Common schema types."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class RunningStyleEnum(str, Enum):
    """Running style enum for API."""

    ESCAPE = "ESCAPE"
    FRONT = "FRONT"
    STALKER = "STALKER"
    CLOSER = "CLOSER"
    VERSATILE = "VERSATILE"


class CourseTypeEnum(str, Enum):
    """Course type enum."""

    TURF = "芝"
    DIRT = "ダート"


class TrackConditionEnum(str, Enum):
    """Track condition enum."""

    GOOD = "良"
    SLIGHTLY_HEAVY = "稍重"
    HEAVY = "重"
    BAD = "不良"


class GradeEnum(str, Enum):
    """Race grade enum."""

    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    OP = "OP"
    L = "L"  # Listed


class WorkoutEvaluationEnum(str, Enum):
    """Workout evaluation enum."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime
