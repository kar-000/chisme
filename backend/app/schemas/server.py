import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=3, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_public: bool = False

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9\-]{1,98}[a-z0-9]$", v):
            raise ValueError(
                "Slug must be lowercase alphanumeric with hyphens, 3–100 chars, and cannot start or end with a hyphen"
            )
        return v


class ServerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    icon_url: str | None = Field(None, max_length=500)
    is_public: bool | None = None


class ServerResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    icon_url: str | None = None
    owner_id: int
    is_public: bool
    is_suspended: bool
    created_at: datetime
    # Computed fields — injected per-request, not stored as columns
    member_count: int | None = None
    current_user_role: str | None = None

    model_config = {"from_attributes": True}


class ServerMembershipResponse(BaseModel):
    user_id: int
    username: str
    avatar_url: str | None = None
    display_name: str | None = None
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}
