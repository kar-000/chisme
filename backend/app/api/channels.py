from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.channel import Channel
from app.models.message import Message
from app.models.user import User
from app.schemas.channel import ChannelCreate, ChannelResponse
from app.schemas.message import MessageCreate, MessageList, MessageResponse

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=List[ChannelResponse])
async def list_channels(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ChannelResponse]:
    channels = (
        db.query(Channel)
        .filter(Channel.is_private == False)  # noqa: E712
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [ChannelResponse.model_validate(c) for c in channels]


@router.post("", response_model=ChannelResponse)
async def create_channel(
    channel_in: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChannelResponse:
    if db.query(Channel).filter(Channel.name == channel_in.name).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Channel name already exists")

    channel = Channel(
        name=channel_in.name,
        description=channel_in.description,
        created_by=current_user.id,
        is_private=channel_in.is_private,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return ChannelResponse.model_validate(channel)


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChannelResponse:
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    if channel.is_private and channel.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to private channel")
    return ChannelResponse.model_validate(channel)


@router.get("/{channel_id}/messages", response_model=MessageList)
async def get_channel_messages(
    channel_id: int,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    before: Optional[datetime] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageList:
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    if channel.is_private and channel.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to channel")

    query = (
        db.query(Message)
        .filter(Message.channel_id == channel_id, Message.is_deleted == False)  # noqa: E712
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


@router.post("/{channel_id}/messages", response_model=MessageResponse)
async def send_message(
    channel_id: int,
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    if channel.is_private and channel.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to channel")

    message = Message(
        content=message_in.content,
        user_id=current_user.id,
        channel_id=channel_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return MessageResponse.model_validate(message)
