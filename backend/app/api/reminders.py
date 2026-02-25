from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.message import Message
from app.models.reminder import Reminder
from app.models.user import User
from app.schemas.message import MessageResponse
from app.schemas.reminder import ReminderCreate, ReminderResponse

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


def _reminder_response(r: Reminder) -> ReminderResponse:
    return ReminderResponse(
        id=r.id,
        message_id=r.message_id,
        remind_at=r.remind_at,
        delivered=r.delivered,
        created_at=r.created_at,
        message=MessageResponse.model_validate(r.message),
    )


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderResponse:
    msg = (
        db.query(Message)
        .filter(
            Message.id == body.message_id,
            Message.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    # remind_at must be in the future
    remind_at = body.remind_at
    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=timezone.utc)
    if remind_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="remind_at must be in the future")

    reminder = Reminder(
        user_id=current_user.id,
        message_id=body.message_id,
        remind_at=remind_at,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return _reminder_response(reminder)


@router.get("", response_model=list[ReminderResponse])
async def list_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReminderResponse]:
    reminders = (
        db.query(Reminder)
        .filter(Reminder.user_id == current_user.id, Reminder.delivered == False)  # noqa: E712
        .order_by(Reminder.remind_at.asc())
        .all()
    )
    return [_reminder_response(r) for r in reminders]


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    reminder = db.query(Reminder).filter_by(id=reminder_id, user_id=current_user.id).first()
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    db.delete(reminder)
    db.commit()
