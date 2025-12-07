"""Race result schemas."""

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class ResultBase(BaseSchema):
    """Base result schema."""

    race_id: int = Field(..., description="レースID")
    horse_id: int = Field(..., description="馬ID")
    jockey_id: int | None = Field(None, description="騎手ID")
    position: int | None = Field(None, ge=1, description="着順")
    time: float | None = Field(None, ge=0, description="タイム(秒)")
    margin: str | None = Field(None, max_length=20, description="着差")
    last_3f: float | None = Field(None, ge=30, le=50, description="上がり3F")
    corner_positions: dict | None = Field(None, description="コーナー通過順")
    prize: int | None = Field(None, ge=0, description="獲得賞金")


class ResultCreate(ResultBase):
    """Schema for creating a result."""

    pass


class ResultUpdate(BaseSchema):
    """Schema for updating a result."""

    position: int | None = Field(None, ge=1)
    time: float | None = Field(None, ge=0)
    margin: str | None = Field(None, max_length=20)
    last_3f: float | None = Field(None, ge=30, le=50)
    corner_positions: dict | None = None
    prize: int | None = Field(None, ge=0)


class ResultResponse(ResultBase, TimestampSchema):
    """Result response schema."""

    id: int
    horse_name: str | None = None
    jockey_name: str | None = None
    race_name: str | None = None


class ResultListResponse(BaseSchema):
    """Result list response schema."""

    items: list[ResultResponse]
    total: int
