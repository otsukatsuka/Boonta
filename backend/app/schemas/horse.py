"""Horse schemas."""

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class HorseBase(BaseSchema):
    """Base horse schema."""

    name: str = Field(..., min_length=1, max_length=50, description="馬名")
    age: int | None = Field(None, ge=2, le=20, description="馬齢")
    sex: str | None = Field(None, max_length=5, description="性別 (牡/牝/セ)")
    trainer: str | None = Field(None, max_length=50, description="調教師")
    owner: str | None = Field(None, max_length=100, description="馬主")


class HorseCreate(HorseBase):
    """Schema for creating a horse."""

    pass


class HorseUpdate(BaseSchema):
    """Schema for updating a horse."""

    name: str | None = Field(None, min_length=1, max_length=50)
    age: int | None = Field(None, ge=2, le=20)
    sex: str | None = Field(None, max_length=5)
    trainer: str | None = Field(None, max_length=50)
    owner: str | None = Field(None, max_length=100)


class HorseResponse(HorseBase, TimestampSchema):
    """Horse response schema."""

    id: int


class HorseListResponse(BaseSchema):
    """Horse list response schema."""

    items: list[HorseResponse]
    total: int
