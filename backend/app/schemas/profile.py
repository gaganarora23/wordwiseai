import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.grade import Grade


class ProfileCreate(BaseModel):
    """Request body for creating and for replacing (PUT) a profile."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nickname: str = Field(min_length=1, max_length=20)
    grade: Grade
    daily_goal: Literal[5, 10]


class Profile(BaseModel):
    """Flat response model; deliberately not built on ProfileCreate (spec 14.4)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nickname: str
    grade: str
    daily_goal: int
    created_at: datetime
    updated_at: datetime
