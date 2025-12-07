"""Pydantic schemas."""

from app.schemas.common import (
    BaseSchema,
    CourseTypeEnum,
    GradeEnum,
    RunningStyleEnum,
    TimestampSchema,
    TrackConditionEnum,
    WorkoutEvaluationEnum,
)
from app.schemas.entry import (
    CommentUpdate,
    EntryCreate,
    EntryListResponse,
    EntryResponse,
    EntryUpdate,
    WorkoutUpdate,
)
from app.schemas.horse import (
    HorseCreate,
    HorseListResponse,
    HorseResponse,
    HorseUpdate,
)
from app.schemas.jockey import (
    JockeyCreate,
    JockeyListResponse,
    JockeyResponse,
    JockeyUpdate,
)
from app.schemas.prediction import (
    BetRecommendation,
    FeatureImportanceResponse,
    HorsePrediction,
    ModelStatusResponse,
    PacePrediction,
    PredictionCreate,
    PredictionHistoryListResponse,
    PredictionHistoryResponse,
    PredictionResponse,
)
from app.schemas.race import (
    RaceCreate,
    RaceDetailResponse,
    RaceListResponse,
    RaceResponse,
    RaceUpdate,
)
from app.schemas.result import (
    ResultCreate,
    ResultListResponse,
    ResultResponse,
    ResultUpdate,
)

__all__ = [
    # Common
    "BaseSchema",
    "TimestampSchema",
    "RunningStyleEnum",
    "CourseTypeEnum",
    "TrackConditionEnum",
    "GradeEnum",
    "WorkoutEvaluationEnum",
    # Race
    "RaceCreate",
    "RaceUpdate",
    "RaceResponse",
    "RaceListResponse",
    "RaceDetailResponse",
    # Horse
    "HorseCreate",
    "HorseUpdate",
    "HorseResponse",
    "HorseListResponse",
    # Jockey
    "JockeyCreate",
    "JockeyUpdate",
    "JockeyResponse",
    "JockeyListResponse",
    # Entry
    "EntryCreate",
    "EntryUpdate",
    "EntryResponse",
    "EntryListResponse",
    "WorkoutUpdate",
    "CommentUpdate",
    # Result
    "ResultCreate",
    "ResultUpdate",
    "ResultResponse",
    "ResultListResponse",
    # Prediction
    "PredictionCreate",
    "PredictionResponse",
    "PredictionHistoryResponse",
    "PredictionHistoryListResponse",
    "HorsePrediction",
    "PacePrediction",
    "BetRecommendation",
    "ModelStatusResponse",
    "FeatureImportanceResponse",
]
