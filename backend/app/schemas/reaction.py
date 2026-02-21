from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserResponse


class ReactionCreate(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=50)


class ReactionResponse(BaseModel):
    id: int
    message_id: int
    user_id: int
    emoji: str
    created_at: datetime
    user: UserResponse

    model_config = {"from_attributes": True}
