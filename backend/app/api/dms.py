import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.dm_channel import DirectMessageChannel
from app.models.message import Message
from app.models.user import User
from app.schemas.dm_channel import DMChannelResponse, DMMessageCreate
from app.schemas.message import MessageList, MessageResponse
from app.schemas.user import UserResponse
from app.websocket.manager import manager

router = APIRouter(prefix="/dms", tags=["dms"])


def _dm_response(dm: DirectMessageChannel, current_user_id: int) -> DMChannelResponse:
    other = dm.other_user(current_user_id)
    return DMChannelResponse(
        id=dm.id,
        other_user=UserResponse.model_validate(other),
        last_message_at=dm.last_message_at,
        created_at=dm.created_at,
    )


@router.get("", response_model=List[DMChannelResponse])
async def list_dms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DMChannelResponse]:
    dms = (
        db.query(DirectMessageChannel)
        .filter(
            (DirectMessageChannel.user1_id == current_user.id)
            | (DirectMessageChannel.user2_id == current_user.id)
        )
        .order_by(DirectMessageChannel.last_message_at.desc())
        .all()
    )
    return [_dm_response(dm, current_user.id) for dm in dms]


@router.post("", response_model=DMChannelResponse, status_code=status.HTTP_200_OK)
async def get_or_create_dm(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DMChannelResponse:
    if other_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot DM yourself")
    other = db.query(User).filter(User.id == other_user_id, User.is_active == True).first()  # noqa: E712
    if not other:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    dm = DirectMessageChannel.get_or_create(db, current_user.id, other_user_id)
    return _dm_response(dm, current_user.id)


@router.get("/{dm_id}/messages", response_model=MessageList)
async def get_dm_messages(
    dm_id: int,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    before: Optional[datetime] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageList:
    dm = db.query(DirectMessageChannel).filter(DirectMessageChannel.id == dm_id).first()
    if not dm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DM not found")
    if current_user.id not in (dm.user1_id, dm.user2_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")

    query = db.query(Message).filter(
        Message.dm_channel_id == dm_id,
        Message.is_deleted == False,  # noqa: E712
    )
    if before:
        query = query.filter(Message.created_at < before)

    total = query.count()
    messages = query.order_by(Message.created_at.desc()).offset(offset).limit(limit).all()

    return MessageList(
        messages=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{dm_id}/messages", response_model=MessageResponse)
async def send_dm_message(
    dm_id: int,
    message_in: DMMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    dm = db.query(DirectMessageChannel).filter(DirectMessageChannel.id == dm_id).first()
    if not dm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DM not found")
    if current_user.id not in (dm.user1_id, dm.user2_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")

    if not message_in.content or not message_in.content.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message cannot be empty")

    # Validate reply_to_id if provided
    if message_in.reply_to_id is not None:
        parent = db.query(Message).filter(
            Message.id == message_in.reply_to_id,
            Message.dm_channel_id == dm_id,
            Message.is_deleted == False,  # noqa: E712
        ).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent message not found")

    msg = Message(
        content=message_in.content.strip(),
        user_id=current_user.id,
        dm_channel_id=dm_id,
        reply_to_id=message_in.reply_to_id,
    )
    db.add(msg)

    dm.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)

    response = MessageResponse.model_validate(msg)

    # Push to both DM participants via WebSocket
    asyncio.ensure_future(manager.broadcast_dm(
        dm_id,
        {"type": "message.new", "message": response.model_dump(mode="json")},
    ))

    return response
