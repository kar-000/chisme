import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import require_server_admin, require_server_member
from app.database import get_db
from app.models.attachment import Attachment
from app.models.channel import Channel
from app.models.message import Message
from app.models.read_receipt import ReadReceipt
from app.models.server_membership import ServerMembership
from app.models.user import User
from app.redis import voice as voice_mgr
from app.schemas.channel import ChannelCreate, ChannelResponse
from app.schemas.message import MessageCreate, MessageList, MessageResponse
from app.schemas.user import UserResponse
from app.services.push_service import send_push_to_user
from app.websocket.manager import manager

router = APIRouter()


def _get_channel_for_server(channel_id: int, server_id: int, db: Session) -> Channel:
    """
    Fetch a channel and verify it belongs to the given server.
    Raises 404 if not found or if the channel belongs to a different server.
    This prevents a member of Server A from accessing channels in Server B
    by guessing channel IDs.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id, Channel.server_id == server_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return channel


def _unread_counts(channel_ids: list[int], user_id: int, db: Session) -> dict[int, int]:
    """Return {channel_id: unread_count} for the given channels and user."""
    if not channel_ids:
        return {}

    rows = (
        db.query(
            Message.channel_id.label("channel_id"),
            func.count(Message.id).label("cnt"),
        )
        .outerjoin(
            ReadReceipt,
            (ReadReceipt.channel_id == Message.channel_id) & (ReadReceipt.user_id == user_id),
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


@router.get(
    "/api/servers/{server_id}/channels",
    response_model=list[ChannelResponse],
)
async def list_channels(
    server_id: int,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    membership: ServerMembership = Depends(require_server_member),
    db: Session = Depends(get_db),
) -> list[ChannelResponse]:
    """Return all non-private channels for this server. Membership required."""
    channels = (
        db.query(Channel)
        .filter(
            Channel.server_id == server_id,
            Channel.is_private == False,  # noqa: E712
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    channel_ids = [c.id for c in channels]
    unread = _unread_counts(channel_ids, membership.user_id, db)

    voice_user_lists = await asyncio.gather(
        *[voice_mgr.get_channel_voice_users(cid) for cid in channel_ids],
        return_exceptions=True,
    )
    voice_counts = {
        cid: len(result) if isinstance(result, list) else 0
        for cid, result in zip(channel_ids, voice_user_lists, strict=False)
    }

    results = []
    for c in channels:
        resp = ChannelResponse.model_validate(c)
        resp.unread_count = unread.get(c.id, 0)
        resp.voice_count = voice_counts.get(c.id, 0)
        results.append(resp)
    return results


@router.post(
    "/api/servers/{server_id}/channels",
    response_model=ChannelResponse,
    status_code=201,
)
async def create_channel(
    server_id: int,
    channel_in: ChannelCreate,
    membership: ServerMembership = Depends(require_server_admin),
    db: Session = Depends(get_db),
) -> ChannelResponse:
    """Create a channel in this server. Admin or owner only."""
    existing = (
        db.query(Channel)
        .filter(
            Channel.server_id == server_id,
            Channel.name == channel_in.name,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A channel with this name already exists in the server",
        )

    channel = Channel(
        name=channel_in.name,
        description=channel_in.description,
        server_id=server_id,
        created_by=membership.user_id,
        is_private=channel_in.is_private,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return ChannelResponse.model_validate(channel)


@router.get(
    "/api/servers/{server_id}/channels/{channel_id}",
    response_model=ChannelResponse,
)
async def get_channel(
    server_id: int,
    channel_id: int,
    membership: ServerMembership = Depends(require_server_member),
    db: Session = Depends(get_db),
) -> ChannelResponse:
    channel = _get_channel_for_server(channel_id, server_id, db)
    if channel.is_private and channel.created_by != membership.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to private channel",
        )
    return ChannelResponse.model_validate(channel)


@router.delete(
    "/api/servers/{server_id}/channels/{channel_id}",
    status_code=204,
)
async def delete_channel(
    server_id: int,
    channel_id: int,
    membership: ServerMembership = Depends(require_server_admin),
    db: Session = Depends(get_db),
) -> None:
    """Delete a channel. Admin or owner only."""
    channel = _get_channel_for_server(channel_id, server_id, db)
    db.delete(channel)
    db.commit()


@router.post(
    "/api/servers/{server_id}/channels/{channel_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def mark_channel_read(
    server_id: int,
    channel_id: int,
    membership: ServerMembership = Depends(require_server_member),
    db: Session = Depends(get_db),
) -> None:
    """Mark all current messages in a channel as read for the requesting user."""
    _get_channel_for_server(channel_id, server_id, db)

    latest = (
        db.query(Message.id)
        .filter(
            Message.channel_id == channel_id,
            Message.is_deleted == False,  # noqa: E712
        )
        .order_by(Message.id.desc())
        .first()
    )
    latest_id = latest[0] if latest else None

    receipt = (
        db.query(ReadReceipt)
        .filter(
            ReadReceipt.user_id == membership.user_id,
            ReadReceipt.channel_id == channel_id,
        )
        .first()
    )

    if receipt:
        if latest_id is not None and (receipt.last_read_message_id is None or latest_id > receipt.last_read_message_id):
            receipt.last_read_message_id = latest_id
    else:
        receipt = ReadReceipt(
            user_id=membership.user_id,
            channel_id=channel_id,
            last_read_message_id=latest_id,
        )
        db.add(receipt)
    db.commit()


@router.get(
    "/api/servers/{server_id}/channels/{channel_id}/members",
    response_model=list[UserResponse],
)
async def get_channel_members(
    server_id: int,
    channel_id: int,
    q: str | None = Query(None, description="Filter by username/display_name prefix"),
    limit: int = Query(10, ge=1, le=20),
    membership: ServerMembership = Depends(require_server_member),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    """Return distinct users who have posted in a channel, optionally filtered."""
    _get_channel_for_server(channel_id, server_id, db)

    q_obj = (
        db.query(User)
        .join(Message, Message.user_id == User.id)
        .filter(
            Message.channel_id == channel_id,
            Message.is_deleted == False,  # noqa: E712
        )
        .distinct()
    )
    if q:
        pattern = f"{q.strip()}%"
        q_obj = q_obj.filter(User.username.ilike(pattern) | User.display_name.ilike(pattern))

    users = q_obj.order_by(User.username).limit(limit).all()
    return [UserResponse.model_validate(u) for u in users]


@router.get(
    "/api/servers/{server_id}/channels/{channel_id}/messages",
    response_model=MessageList,
)
async def get_channel_messages(
    server_id: int,
    channel_id: int,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    before: datetime | None = Query(default=None),
    membership: ServerMembership = Depends(require_server_member),
    db: Session = Depends(get_db),
) -> MessageList:
    channel = _get_channel_for_server(channel_id, server_id, db)
    if channel.is_private and channel.created_by != membership.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to channel")

    query = db.query(Message).filter(
        Message.channel_id == channel_id,
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


@router.post(
    "/api/servers/{server_id}/channels/{channel_id}/messages",
    response_model=MessageResponse,
)
async def send_message(
    server_id: int,
    channel_id: int,
    message_in: MessageCreate,
    membership: ServerMembership = Depends(require_server_member),
    db: Session = Depends(get_db),
) -> MessageResponse:
    channel = _get_channel_for_server(channel_id, server_id, db)
    if channel.is_private and channel.created_by != membership.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to channel")

    if message_in.reply_to_id is not None:
        parent = (
            db.query(Message)
            .filter(
                Message.id == message_in.reply_to_id,
                Message.channel_id == channel_id,
                Message.is_deleted == False,  # noqa: E712
            )
            .first()
        )
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message to reply to not found in this channel",
            )

    current_user_id = membership.user_id
    message = Message(
        content=message_in.content,
        user_id=current_user_id,
        channel_id=channel_id,
        reply_to_id=message_in.reply_to_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    if message_in.attachment_ids:
        db.query(Attachment).filter(
            Attachment.id.in_(message_in.attachment_ids),
            Attachment.user_id == current_user_id,
            Attachment.message_id.is_(None),
        ).update({"message_id": message.id}, synchronize_session=False)
        db.commit()
        db.refresh(message)

    response = MessageResponse.model_validate(message)

    # Broadcast to all server members connected via WebSocket.
    # Payload includes channel_id so the frontend routes it to the right channel.
    asyncio.ensure_future(
        manager.broadcast_to_server(
            server_id,
            {
                "type": "message.new",
                "channel_id": channel_id,
                "message": response.model_dump(mode="json"),
            },
        )
    )

    # Push notifications for @mentioned users not currently connected to the server
    if message_in.content:
        current_user = db.query(User).filter(User.id == current_user_id).first()
        connected_users = set(manager.get_server_users(server_id))
        words = message_in.content.lower().split()
        mentioned_names = {w.lstrip("@") for w in words if w.startswith("@")}
        if mentioned_names:
            mentioned_users = (
                db.query(User)
                .filter(
                    User.username.in_(mentioned_names),
                    User.id != current_user_id,
                )
                .all()
            )
            for target in mentioned_users:
                if target.id not in connected_users:
                    send_push_to_user(
                        user_id=target.id,
                        title=(f"@{current_user.username} mentioned you in #{channel.name}"),
                        body=message_in.content[:100],
                        url=f"/?channel={channel_id}",
                        tag=f"mention-{message.id}",
                        db=db,
                    )

    return response
