from datetime import datetime

from pydantic import BaseModel


class ChannelNotesResponse(BaseModel):
    id: int
    channel_id: int
    content: str | None
    updated_by: int | None
    updated_by_username: str | None
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


class ChannelNotesUpdate(BaseModel):
    content: str | None = None
    base_version: int | None = None  # for optimistic concurrency


class ChannelNotesHistoryEntry(BaseModel):
    id: int
    version: int
    content: str | None
    edited_by: int
    edited_by_username: str | None
    edited_at: datetime

    model_config = {"from_attributes": True}
