"""Background task: deliver due reminders via WebSocket.

The scheduler runs every 30 seconds and pushes `reminder_due` events to
connected users whose quiet-hours window has passed.
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import SessionLocal
from app.models.reminder import Reminder
from app.services.notification_service import is_user_in_quiet_hours
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("interval", seconds=30, id="deliver_reminders")
async def deliver_reminders() -> None:
    """Query overdue reminders and push them to connected users."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        pending = (
            db.query(Reminder)
            .filter(
                Reminder.delivered == False,  # noqa: E712
                Reminder.remind_at <= now,
            )
            .all()
        )

        for reminder in pending:
            user = reminder.user
            if is_user_in_quiet_hours(user):
                # Retry on the next tick when quiet hours end
                continue

            reminder.delivered = True

            msg = reminder.message
            payload = {
                "type": "reminder_due",
                "reminder": {
                    "id": reminder.id,
                    "message_id": reminder.message_id,
                    "remind_at": reminder.remind_at.isoformat(),
                    "message": {
                        "id": msg.id,
                        "content": msg.content or "",
                        "user": {
                            "username": msg.user.username if msg.user else "unknown",
                        },
                        "channel_id": msg.channel_id,
                        "server_id": msg.channel.server_id if msg.channel else None,
                    },
                },
            }
            await manager.send_to_user(reminder.user_id, payload)

        db.commit()
    except Exception:
        logger.exception("Error in deliver_reminders task")
        db.rollback()
    finally:
        db.close()
