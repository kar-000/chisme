from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.message import MessageResponse


class BookmarkCreate(BaseModel):
    message_id: int
    note: str | None = Field(None, max_length=200)


class BookmarkUpdate(BaseModel):
    note: str | None = Field(None, max_length=200)


class BookmarkResponse(BaseModel):
    id: int
    message_id: int
    note: str | None
    created_at: datetime
    message: MessageResponse

    model_config = {"from_attributes": True}
