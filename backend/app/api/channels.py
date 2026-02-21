import asyncio
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.attachment import Attachment
from app.models.channel import Channel
from app.models.message import Message
from app.models.read_receipt import ReadReceipt
from app.models.user import User
from app.schemas.channel import ChannelCreate, ChannelResponse
from app.schemas.message import MessageCreate, MessageList, MessageResponse
from app.websocket.manager import manager

router = APIRouter(prefix="/channels", tags=["channels"])


def _unread_counts(channel_ids: list[int], user_id: int, db: Session) -> dict[int, int]:
    """Return {channel_id: unread_count} for the given channels and user.

    A message is unread if its id is greater than the user's last_read_message_id
    for that channel, or if the user has no receipt at all.
    """
    if not channel_ids:
        return {}

    rows = (
        db.query(
            Message.channel_id.label("channel_id"),
            func.count(Message.id).label("cnt"),
        )
        .outerjoin(
            ReadReceipt,
            (ReadReceipt.channel_id == Message.channel_id)
            & (ReadReceipt.user_id == user_id),
        )
        .filter(
            Message.channel_id.in_(channel_ids),
            Message.is_deleted == False,  # noqa: E712
            or_(
                ReadReceipt.last_read_message_id == None,  # noqa: E711
                Message.id > ReadReceipt.last_read_message_id,
            ),
        )
        .group_by(Message.channel_id)
        .all()
    )
    return {row.channel_id: row.cnt for row in rows}


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
    channel_ids = [c.id for c in channels]
    unread = _unread_counts(channel_ids, current_user.id, db)

    results = []
    for c in channels:
        resp = ChannelResponse.model_validate(c)
        resp.unread_count = unread.get(c.id, 0)
        results.append(resp)
    return results


@router.post("/{channel_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_channel_read(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Mark all current messages in a channel as read for the requesting user."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    # Find the latest message in the channel
    latest = (
        db.query(Message.id)
        .filter(Message.channel_id == channel_id, Message.is_deleted == False)  # noqa: E712
        .order_by(Message.id.desc())
        .first()
    )
    latest_id = latest[0] if latest else None

    receipt = db.query(ReadReceipt).filter(
        ReadReceipt.user_id == current_user.id,
        ReadReceipt.channel_id == channel_id,
    ).first()

    if receipt:
        # Only advance — never go backwards (in case of race conditions)
        if latest_id is not None and (receipt.last_read_message_id is None or latest_id > receipt.last_read_message_id):
            receipt.last_read_message_id = latest_id
    else:
        receipt = ReadReceipt(
            user_id=current_user.id,
            channel_id=channel_id,
            last_read_message_id=latest_id,
        )
        db.add(receipt)
    db.commit()


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

    # Validate reply_to_id if provided
    if message_in.reply_to_id is not None:
        parent = db.query(Message).filter(
            Message.id == message_in.reply_to_id,
            Message.channel_id == channel_id,
            Message.is_deleted == False,  # noqa: E712
        ).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message to reply to not found in this channel",
            )

    message = Message(
        content=message_in.content,
        user_id=current_user.id,
        channel_id=channel_id,
        reply_to_id=message_in.reply_to_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Link any pre-uploaded attachments to this message
    if message_in.attachment_ids:
        db.query(Attachment).filter(
            Attachment.id.in_(message_in.attachment_ids),
            Attachment.user_id == current_user.id,
            Attachment.message_id.is_(None),
        ).update({"message_id": message.id}, synchronize_session=False)
        db.commit()
        db.refresh(message)

    response = MessageResponse.model_validate(message)

    # Broadcast new message to all connected channel clients
    asyncio.ensure_future(manager.broadcast(
        channel_id,
        {"type": "message.new", "message": response.model_dump(mode="json")},
    ))

    return response
