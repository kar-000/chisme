from datetime import datetime

from pydantic import BaseModel, Field


class PollOptionResponse(BaseModel):
    id: int
    text: str
    order: int
    votes: int
    percentage: float

    model_config = {"from_attributes": True}


class PollResponse(BaseModel):
    id: int
    message_id: int
    question: str
    multi_choice: bool
    closes_at: datetime | None
    created_by: int
    total_votes: int
    options: list[PollOptionResponse]
    user_voted_option_ids: list[int] = []

    model_config = {"from_attributes": True}


class PollCreate(BaseModel):
    channel_id: int
    server_id: int
    question: str = Field(..., min_length=1, max_length=300)
    options: list[str] = Field(..., min_length=2, max_length=6)
    multi_choice: bool = False
    expires_in_hours: int | None = None  # None = no expiry; 1, 6, 24, 72


class PollVoteRequest(BaseModel):
    option_ids: list[int]
