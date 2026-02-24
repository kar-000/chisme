from datetime import datetime

from pydantic import BaseModel

from app.schemas.message import MessageResponse


class ReminderCreate(BaseModel):
    message_id: int
    remind_at: datetime


class ReminderResponse(BaseModel):
    id: int
    message_id: int
    remind_at: datetime
    delivered: bool
    created_at: datetime
    message: MessageResponse

    model_config = {"from_attributes": True}
