from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, List

from app.schemas.user import UserResponse
from app.schemas.reaction import ReactionResponse
from app.schemas.attachment import AttachmentResponse


class QuotedMessageResponse(BaseModel):
    """Minimal snapshot of the parent message embedded in a reply."""
    id: int
    content: str
    user: UserResponse

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field("", max_length=2000)
    attachment_ids: List[int] = []
    reply_to_id: Optional[int] = None

    @model_validator(mode="after")
    def require_content_or_attachment(self) -> "MessageCreate":
        if not self.content.strip() and not self.attachment_ids:
            raise ValueError("Message must have content or at least one attachment")
        return self


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    id: int
    content: str
    user_id: int
    channel_id: Optional[int] = None
    dm_channel_id: Optional[int] = None
    reply_to_id: Optional[int] = None
    reply_to: Optional[QuotedMessageResponse] = None
    created_at: datetime
    edited_at: Optional[datetime] = None
    user: UserResponse
    reactions: List[ReactionResponse] = []
    attachments: List[AttachmentResponse] = []

    model_config = {"from_attributes": True}


class MessageList(BaseModel):
    messages: List[MessageResponse]
    total: int
    limit: int
    offset: int
