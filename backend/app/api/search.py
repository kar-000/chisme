"""
Message search endpoint.

GET /api/search/messages?q=...&channel_id=...&limit=50

Results are restricted to channels the requesting user is a member of
(all public channels) and DMs they participate in.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.message import Message
from app.models.user import User

router = APIRouter(prefix="/search", tags=["search"])

_MAX_LIMIT = 100


class SearchResultUser(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None


class SearchResultItem(BaseModel):
    id: int
    content: str
    user: SearchResultUser
    channel_id: int | None = None
    channel_name: str | None = None
    dm_channel_id: int | None = None
    created_at: str
    edited_at: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int


@router.get("/messages", response_model=SearchResponse)
async def search_messages(
    q: str = Query(..., min_length=1, description="Search query"),
    channel_id: int | None = Query(None, description="Restrict to a specific channel"),
    limit: int = Query(50, ge=1, le=_MAX_LIMIT),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Full-text search across messages visible to the current user."""
    if not q.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="q must not be blank")

    query = db.query(Message).filter(
        Message.is_deleted == False,  # noqa: E712
        Message.content.ilike(f"%{q.strip()}%"),
        # Only channel messages (not DMs) for now — DM privacy
        Message.channel_id.isnot(None),
    )

    if channel_id is not None:
        query = query.filter(Message.channel_id == channel_id)

    messages = query.order_by(Message.created_at.desc()).limit(limit).all()

    results = [
        SearchResultItem(
            id=msg.id,
            content=msg.content,
            user=SearchResultUser(
                id=msg.user.id,
                username=msg.user.username,
                display_name=msg.user.display_name,
                avatar_url=msg.user.avatar_url,
            ),
            channel_id=msg.channel_id,
            channel_name=msg.channel.name if msg.channel else None,
            created_at=msg.created_at.isoformat(),
            edited_at=msg.edited_at.isoformat() if msg.edited_at else None,
        )
        for msg in messages
    ]

    return SearchResponse(results=results, total=len(results))
