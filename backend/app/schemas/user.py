from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must be alphanumeric with optional underscores")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_lowercase(cls, v: str) -> str:
        return v.lower()


class UserResponse(UserBase):
    id: int
    avatar_url: str | None = None
    display_name: str | None = None
    bio: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    avatar_url: str | None = None
    display_name: str | None = Field(None, max_length=50)
    bio: str | None = Field(None, max_length=500)
    status: str | None = Field(None, max_length=100)
