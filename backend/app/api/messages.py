from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.message import Message
from app.models.reaction import Reaction
from app.models.user import User
from app.schemas.message import MessageResponse, MessageUpdate
from app.schemas.reaction import ReactionCreate, ReactionResponse

router = APIRouter(prefix="/messages", tags=["messages"])

EDIT_WINDOW_HOURS = 24


@router.put("/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: int,
    message_in: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    message = db.query(Message).filter(Message.id == message_id, Message.is_deleted == False).first()  # noqa: E712
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if message.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the message author")

    created_at = message.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) - created_at > timedelta(hours=EDIT_WINDOW_HOURS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit window of 24 hours has expired",
        )

    message.content = message_in.content
    message.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return MessageResponse.model_validate(message)


@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    message = db.query(Message).filter(Message.id == message_id, Message.is_deleted == False).first()  # noqa: E712
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if message.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the message author")

    message.is_deleted = True
    db.commit()
    return {"success": True}


@router.post("/{message_id}/reactions", response_model=ReactionResponse)
async def add_reaction(
    message_id: int,
    reaction_in: ReactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReactionResponse:
    message = db.query(Message).filter(Message.id == message_id, Message.is_deleted == False).first()  # noqa: E712
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    existing = (
        db.query(Reaction)
        .filter(
            Reaction.message_id == message_id,
            Reaction.user_id == current_user.id,
            Reaction.emoji == reaction_in.emoji,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already reacted with this emoji",
        )

    reaction = Reaction(
        message_id=message_id,
        user_id=current_user.id,
        emoji=reaction_in.emoji,
    )
    db.add(reaction)
    db.commit()
    db.refresh(reaction)
    return ReactionResponse.model_validate(reaction)


@router.delete("/{message_id}/reactions/{emoji}")
async def remove_reaction(
    message_id: int,
    emoji: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    reaction = (
        db.query(Reaction)
        .filter(
            Reaction.message_id == message_id,
            Reaction.user_id == current_user.id,
            Reaction.emoji == emoji,
        )
        .first()
    )
    if not reaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reaction not found")

    db.delete(reaction)
    db.commit()
    return {"success": True}
