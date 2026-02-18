from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

from app.schemas.user import UserResponse
from app.schemas.reaction import ReactionResponse


class MessageBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class MessageCreate(MessageBase):
    pass


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(MessageBase):
    id: int
    user_id: int
    channel_id: int
    created_at: datetime
    edited_at: Optional[datetime] = None
    user: UserResponse
    reactions: List[ReactionResponse] = []

    model_config = {"from_attributes": True}


class MessageList(BaseModel):
    messages: List[MessageResponse]
    total: int
    limit: int
    offset: int
