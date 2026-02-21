from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserResponse


class DMChannelResponse(BaseModel):
    id: int
    other_user: UserResponse
    last_message_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DMMessageCreate(BaseModel):
    content: str
    reply_to_id: int | None = None
