import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.channel import Channel
from app.models.message import Message
from app.models.poll import Poll, PollOption, PollVote
from app.models.server_membership import ServerMembership
from app.models.user import User
from app.schemas.message import MessageResponse
from app.schemas.poll import PollCreate, PollOptionResponse, PollResponse, PollVoteRequest
from app.websocket.manager import manager

router = APIRouter(prefix="/api/polls", tags=["polls"])


def _build_poll_response(poll: Poll, user_voted_option_ids: list[int]) -> PollResponse:
    """Build a PollResponse with computed vote counts and user vote state."""
    total = sum(len(o.votes) for o in poll.options)
    options = []
    for opt in poll.options:
        votes = len(opt.votes)
        pct = round(votes / total * 100, 1) if total > 0 else 0.0
        options.append(PollOptionResponse(id=opt.id, text=opt.text, order=opt.order, votes=votes, percentage=pct))
    return PollResponse(
        id=poll.id,
        message_id=poll.message_id,
        question=poll.question,
        multi_choice=poll.multi_choice,
        closes_at=poll.closes_at,
        created_by=poll.created_by,
        total_votes=total,
        options=options,
        user_voted_option_ids=user_voted_option_ids,
    )


def _get_user_voted_ids(poll_id: int, user_id: int, db: Session) -> list[int]:
    return [
        row.option_id
        for row in (
            db.query(PollVote.option_id)
            .join(PollOption, PollOption.id == PollVote.option_id)
            .filter(PollOption.poll_id == poll_id, PollVote.user_id == user_id)
            .all()
        )
    ]


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_poll(
    body: PollCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Create a poll in a channel. Creates a message + poll row atomically."""
    if len(body.options) < 2 or len(body.options) > 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Polls must have 2–6 options",
        )

    membership = db.query(ServerMembership).filter_by(server_id=body.server_id, user_id=current_user.id).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a server member")

    channel = db.query(Channel).filter_by(id=body.channel_id, server_id=body.server_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    # Create the backing message
    message = Message(content=body.question, user_id=current_user.id, channel_id=body.channel_id)
    db.add(message)
    db.flush()  # get message.id

    closes_at = None
    if body.expires_in_hours:
        closes_at = datetime.now(timezone.utc) + timedelta(hours=body.expires_in_hours)

    poll = Poll(
        message_id=message.id,
        question=body.question,
        multi_choice=body.multi_choice,
        closes_at=closes_at,
        created_by=current_user.id,
    )
    db.add(poll)
    db.flush()  # get poll.id

    for i, text in enumerate(body.options):
        db.add(PollOption(poll_id=poll.id, text=text.strip(), order=i))

    db.commit()
    db.refresh(message)
    db.refresh(poll)

    poll_resp = _build_poll_response(poll, [])
    msg_resp = MessageResponse.model_validate(message)
    msg_resp.poll = poll_resp

    asyncio.ensure_future(
        manager.broadcast_to_server(
            body.server_id,
            {
                "type": "message.new",
                "channel_id": body.channel_id,
                "message": msg_resp.model_dump(mode="json"),
            },
        )
    )

    return msg_resp


@router.get("/{poll_id}", response_model=PollResponse)
async def get_poll(
    poll_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PollResponse:
    poll = db.query(Poll).filter_by(id=poll_id).first()
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")
    user_voted_ids = _get_user_voted_ids(poll_id, current_user.id, db)
    return _build_poll_response(poll, user_voted_ids)


@router.post("/{poll_id}/vote", response_model=PollResponse)
async def cast_vote(
    poll_id: int,
    body: PollVoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PollResponse:
    poll = db.query(Poll).filter_by(id=poll_id).first()
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")

    now = datetime.now(timezone.utc)
    if poll.closes_at:
        closes = poll.closes_at
        if closes.tzinfo is None:
            closes = closes.replace(tzinfo=timezone.utc)
        if closes < now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Poll is closed")

    if not body.option_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No option IDs provided")

    valid_ids = {o.id for o in poll.options}
    for oid in body.option_ids:
        if oid not in valid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Option {oid} does not belong to this poll",
            )

    if not poll.multi_choice and len(body.option_ids) > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Poll does not allow multiple choices")

    # Remove existing votes for this user on this poll
    existing = (
        db.query(PollVote)
        .join(PollOption, PollOption.id == PollVote.option_id)
        .filter(PollOption.poll_id == poll_id, PollVote.user_id == current_user.id)
        .all()
    )
    for v in existing:
        db.delete(v)

    for oid in body.option_ids:
        db.add(PollVote(option_id=oid, user_id=current_user.id))

    db.commit()
    db.refresh(poll)

    poll_resp = _build_poll_response(poll, list(body.option_ids))

    # Broadcast poll_updated to channel
    msg = db.query(Message).filter_by(id=poll.message_id).first()
    if msg and msg.channel_id:
        server_id = db.query(Channel.server_id).filter_by(id=msg.channel_id).scalar()
        if server_id:
            asyncio.ensure_future(
                manager.broadcast_to_server(
                    server_id,
                    {
                        "type": "poll_updated",
                        "channel_id": msg.channel_id,
                        "message_id": poll.message_id,
                        "poll_id": poll.id,
                        "options": [
                            {
                                "id": o.id,
                                "votes": o.votes,
                                "percentage": o.percentage,
                            }
                            for o in poll_resp.options
                        ],
                        "total_votes": poll_resp.total_votes,
                    },
                )
            )

    return poll_resp


@router.delete("/{poll_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def remove_vote(
    poll_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    poll = db.query(Poll).filter_by(id=poll_id).first()
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")

    now = datetime.now(timezone.utc)
    if poll.closes_at:
        closes = poll.closes_at
        if closes.tzinfo is None:
            closes = closes.replace(tzinfo=timezone.utc)
        if closes < now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Poll is closed")

    existing = (
        db.query(PollVote)
        .join(PollOption, PollOption.id == PollVote.option_id)
        .filter(PollOption.poll_id == poll_id, PollVote.user_id == current_user.id)
        .all()
    )
    for v in existing:
        db.delete(v)
    db.commit()

    # Broadcast updated counts
    db.refresh(poll)
    poll_resp = _build_poll_response(poll, [])
    msg = db.query(Message).filter_by(id=poll.message_id).first()
    if msg and msg.channel_id:
        server_id = db.query(Channel.server_id).filter_by(id=msg.channel_id).scalar()
        if server_id:
            asyncio.ensure_future(
                manager.broadcast_to_server(
                    server_id,
                    {
                        "type": "poll_updated",
                        "channel_id": msg.channel_id,
                        "message_id": poll.message_id,
                        "poll_id": poll.id,
                        "options": [
                            {"id": o.id, "votes": o.votes, "percentage": o.percentage} for o in poll_resp.options
                        ],
                        "total_votes": poll_resp.total_votes,
                    },
                )
            )
