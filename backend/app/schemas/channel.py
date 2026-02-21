from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserResponse


class ChannelBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: str | None = Field(None, max_length=500)


class ChannelCreate(ChannelBase):
    is_private: bool = False

    @field_validator("name")
    @classmethod
    def name_lowercase_alphanumeric(cls, v: str) -> str:
        if not v.replace("-", "").isalnum():
            raise ValueError("Channel name must be alphanumeric with optional hyphens")
        return v.lower()


class ChannelResponse(ChannelBase):
    id: int
    created_by: int
    is_private: bool
    created_at: datetime
    creator: UserResponse

    unread_count: int = 0

    model_config = {"from_attributes": True}
