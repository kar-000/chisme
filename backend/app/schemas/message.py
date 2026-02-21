from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.attachment import AttachmentResponse
from app.schemas.reaction import ReactionResponse
from app.schemas.user import UserResponse


class QuotedMessageResponse(BaseModel):
    """Minimal snapshot of the parent message embedded in a reply."""

    id: int
    content: str
    user: UserResponse

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field("", max_length=2000)
    attachment_ids: list[int] = []
    reply_to_id: int | None = None

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
    channel_id: int | None = None
    dm_channel_id: int | None = None
    reply_to_id: int | None = None
    reply_to: QuotedMessageResponse | None = None
    created_at: datetime
    edited_at: datetime | None = None
    user: UserResponse
    reactions: list[ReactionResponse] = []
    attachments: list[AttachmentResponse] = []

    model_config = {"from_attributes": True}


class MessageList(BaseModel):
    messages: list[MessageResponse]
    total: int
    limit: int
    offset: int
