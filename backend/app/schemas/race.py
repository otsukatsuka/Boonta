"""Race schemas."""

from datetime import date

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class RaceBase(BaseSchema):
    """Base race schema."""

    name: str = Field(..., min_length=1, max_length=100, description="レース名")
    date: date = Field(..., description="開催日")
    venue: str = Field(..., min_length=1, max_length=20, description="競馬場")
    course_type: str = Field(..., min_length=1, max_length=10, description="芝/ダート")
    distance: int = Field(..., ge=800, le=4000, description="距離(m)")
    track_condition: str | None = Field(None, max_length=10, description="馬場状態")
    weather: str | None = Field(None, max_length=10, description="天気")
    grade: str = Field(..., min_length=1, max_length=10, description="グレード")
    purse: int | None = Field(None, ge=0, description="賞金(万円)")


class RaceCreate(RaceBase):
    """Schema for creating a race."""

    pass


class RaceUpdate(BaseSchema):
    """Schema for updating a race."""

    name: str | None = Field(None, min_length=1, max_length=100)
    date: date | None = None
    venue: str | None = Field(None, min_length=1, max_length=20)
    course_type: str | None = Field(None, min_length=1, max_length=10)
    distance: int | None = Field(None, ge=800, le=4000)
    track_condition: str | None = Field(None, max_length=10)
    weather: str | None = Field(None, max_length=10)
    grade: str | None = Field(None, min_length=1, max_length=10)
    purse: int | None = Field(None, ge=0)


class RaceResponse(RaceBase, TimestampSchema):
    """Race response schema."""

    id: int
    entries_count: int | None = Field(None, description="出走頭数")


class RaceListResponse(BaseSchema):
    """Race list response schema."""

    items: list[RaceResponse]
    total: int


class RaceDetailResponse(RaceResponse):
    """Race detail response with entries."""

    from app.schemas.entry import EntryResponse

    entries: list[EntryResponse] = Field(default_factory=list)
