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
from app.models.poll import Poll, PollOption, PollVote
from app.models.read_receipt import ReadReceipt
from app.models.server_membership import ServerMembership
from app.models.user import User
from app.redis import voice as voice_mgr
from app.schemas.channel import ChannelCreate, ChannelResponse
from app.schemas.message import MessageCreate, MessageList, MessageResponse
from app.schemas.user import UserResponse
from app.services.notification_service import should_notify_for_channel_message
from app.services.push_service import send_push_to_user
from app.services.user_service import get_display_name
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
            Message.user_id != user_id,  # own messages never count as unread
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

    # Batch-fetch poll data for any poll messages
    message_ids = [m.id for m in messages]
    polls_by_message_id: dict[int, Poll] = {}
    user_voted_by_poll: dict[int, list[int]] = {}
    if message_ids:
        polls = db.query(Poll).filter(Poll.message_id.in_(message_ids)).all()
        if polls:
            polls_by_message_id = {p.message_id: p for p in polls}
            poll_ids = [p.id for p in polls]
            vote_rows = (
                db.query(PollVote.option_id, PollOption.poll_id)
                .join(PollOption, PollOption.id == PollVote.option_id)
                .filter(PollOption.poll_id.in_(poll_ids), PollVote.user_id == membership.user_id)
                .all()
            )
            for option_id, poll_id in vote_rows:
                user_voted_by_poll.setdefault(poll_id, []).append(option_id)

    def _build_poll_resp(poll: Poll, voted_ids: list[int]):
        from app.schemas.poll import PollOptionResponse, PollResponse

        total_v = sum(len(o.votes) for o in poll.options)
        opts = []
        for opt in poll.options:
            v = len(opt.votes)
            pct = round(v / total_v * 100, 1) if total_v > 0 else 0.0
            opts.append(PollOptionResponse(id=opt.id, text=opt.text, order=opt.order, votes=v, percentage=pct))
        return PollResponse(
            id=poll.id,
            message_id=poll.message_id,
            question=poll.question,
            multi_choice=poll.multi_choice,
            closes_at=poll.closes_at,
            created_by=poll.created_by,
            total_votes=total_v,
            options=opts,
            user_voted_option_ids=voted_ids,
        )

    # Batch-fetch server memberships to resolve nicknames for all message authors
    author_ids = {m.user_id for m in messages}
    memberships_by_user: dict[int, ServerMembership] = {}
    if author_ids:
        mem_rows = (
            db.query(ServerMembership)
            .filter(
                ServerMembership.server_id == channel.server_id,
                ServerMembership.user_id.in_(author_ids),
            )
            .all()
        )
        memberships_by_user = {mem.user_id: mem for mem in mem_rows}

    msg_responses = []
    for m in messages:
        resp = MessageResponse.model_validate(m)
        # Inject resolved display_name (nickname → display_name → username)
        mem = memberships_by_user.get(m.user_id)
        if mem and mem.nickname and resp.user:
            resp.user = resp.user.model_copy(update={"display_name": mem.nickname})
        if m.id in polls_by_message_id:
            poll = polls_by_message_id[m.id]
            resp.poll = _build_poll_resp(poll, user_voted_by_poll.get(poll.id, []))
        msg_responses.append(resp)

    return MessageList(
        messages=msg_responses,
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

    # Inject the sender's resolved display_name (nickname → display_name → username)
    # into the broadcast payload so all receivers see the correct name immediately.
    if response.user:
        display_name = get_display_name(message.user, membership)
        response.user = response.user.model_copy(update={"display_name": display_name})

    # Broadcast to all server members connected via WebSocket.
    # Payload includes channel_id so the frontend routes it to the right channel.
    asyncio.ensure_future(
        manager.broadcast_to_server(
            server_id,
            {
                "type": "message.new",
                "channel_id": channel_id,
                "channel_name": channel.name,
                "server_name": membership.server.name,
                "message": response.model_dump(mode="json"),
            },
        )
    )

    # Centralised notification dispatch.
    # message.user is already loaded above (get_display_name call); use it to
    # avoid an extra DB round-trip.
    sender_username = message.user.username
    all_members = (
        db.query(User)
        .join(ServerMembership, ServerMembership.user_id == User.id)
        .filter(
            ServerMembership.server_id == server_id,
            User.id != current_user_id,
        )
        .all()
    )
    content = message_in.content or ""
    body = content[:100] if content else "(attachment)"
    global_notifications: list[tuple[int, dict]] = []

    for member in all_members:
        should, title, tag, is_mention = should_notify_for_channel_message(
            member,
            sender_id=current_user_id,
            sender_username=sender_username,
            content=content,
            channel_name=channel.name,
            server_name=membership.server.name,
            channel_id=channel_id,
            db=db,
        )
        if not should:
            continue
        payload = {
            "type": "notification",
            "channel_id": channel_id,
            "server_id": server_id,
            "title": title,
            "body": body,
            "tag": tag,
            "is_mention": is_mention,
        }
        if manager.is_globally_connected(member.id):
            global_notifications.append((member.id, payload))
        else:
            send_push_to_user(
                user_id=member.id,
                title=title,
                body=body,
                url=f"/?channel={channel_id}",
                tag=tag,
                db=db,
            )

    if global_notifications:

        async def _fire_notifications(items: list[tuple[int, dict]]) -> None:
            for uid, p in items:
                await manager.send_global_notification(uid, p)

        asyncio.ensure_future(_fire_notifications(global_notifications))

    return response
