"""
Message search endpoint.

GET /api/search/messages?q=...&channel_id=...&limit=50
  Optional filters: from_user, after, before, has_link, has_file

Results are restricted to channels the requesting user is a member of
(all public channels) and DMs they participate in.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.attachment import Attachment
from app.models.message import Message
from app.models.user import User

router = APIRouter(prefix="/search", tags=["search"])

_MAX_LIMIT = 100


def _escape_like(s: str) -> str:
    """Escape SQL LIKE special characters so user input is treated as a literal string."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
    q: str = Query(default="", description="Search query (optional when filters are set)"),
    channel_id: int | None = Query(None, description="Restrict to a specific channel"),
    from_user: str | None = Query(None, description="Filter by username (partial match)"),
    after: date | None = Query(None, description="Messages on or after this date (YYYY-MM-DD)"),
    before: date | None = Query(None, description="Messages before this date (YYYY-MM-DD)"),
    has_link: bool = Query(False, description="Only messages containing http(s) URLs"),
    has_file: bool = Query(False, description="Only messages with file attachments"),
    limit: int = Query(50, ge=1, le=_MAX_LIMIT),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Full-text search across messages visible to the current user with optional filters."""
    if not q.strip() and not any([channel_id, from_user, after, before, has_link, has_file]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide a query or at least one filter",
        )

    query = (
        db.query(Message)
        .join(User, Message.user_id == User.id)
        .filter(
            Message.is_deleted == False,  # noqa: E712
            # Only channel messages (not DMs) for now — DM privacy
            Message.channel_id.isnot(None),
        )
    )

    if q.strip():
        query = query.filter(Message.content.ilike(f"%{_escape_like(q.strip())}%", escape="\\"))

    if channel_id is not None:
        query = query.filter(Message.channel_id == channel_id)

    if from_user:
        query = query.filter(User.username.ilike(f"%{_escape_like(from_user)}%", escape="\\"))

    if after is not None:
        query = query.filter(Message.created_at >= after)

    if before is not None:
        query = query.filter(Message.created_at < before)

    if has_link:
        query = query.filter(Message.content.op("~*")(r"https?://"))

    if has_file:
        query = query.filter(db.query(Attachment).filter(Attachment.message_id == Message.id).exists())

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
