"""Jockey schemas."""

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class JockeyBase(BaseSchema):
    """Base jockey schema."""

    name: str = Field(..., min_length=1, max_length=50, description="騎手名")
    win_rate: float | None = Field(None, ge=0, le=1, description="勝率")
    place_rate: float | None = Field(None, ge=0, le=1, description="複勝率")
    venue_win_rate: float | None = Field(None, ge=0, le=1, description="競馬場別勝率")


class JockeyCreate(JockeyBase):
    """Schema for creating a jockey."""

    pass


class JockeyUpdate(BaseSchema):
    """Schema for updating a jockey."""

    name: str | None = Field(None, min_length=1, max_length=50)
    win_rate: float | None = Field(None, ge=0, le=1)
    place_rate: float | None = Field(None, ge=0, le=1)
    venue_win_rate: float | None = Field(None, ge=0, le=1)


class JockeyResponse(JockeyBase, TimestampSchema):
    """Jockey response schema."""

    id: int


class JockeyListResponse(BaseSchema):
    """Jockey list response schema."""

    items: list[JockeyResponse]
    total: int
