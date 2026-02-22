"""
Web Push subscription management.

GET  /push/vapid-public-key  — return the VAPID public key for frontend subscription
POST /push/subscribe          — upsert a push subscription for the current user
DELETE /push/unsubscribe      — remove a push subscription
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.push_subscription import PushSubscription
from app.models.user import User

router = APIRouter(prefix="/push", tags=["push"])


class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: dict  # {"p256dh": str, "auth": str}


class UnsubscribeRequest(BaseModel):
    endpoint: str


@router.get("/vapid-public-key")
async def get_vapid_public_key() -> dict:
    """Return the VAPID public key so the frontend can subscribe."""
    return {"key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe(
    data: PushSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Upsert a browser push subscription for the current user."""
    existing = db.query(PushSubscription).filter_by(endpoint=data.endpoint).first()
    if existing:
        existing.user_id = current_user.id
        existing.p256dh = data.keys["p256dh"]
        existing.auth = data.keys["auth"]
    else:
        db.add(
            PushSubscription(
                user_id=current_user.id,
                endpoint=data.endpoint,
                p256dh=data.keys["p256dh"],
                auth=data.keys["auth"],
            )
        )
    db.commit()
    return {"status": "subscribed"}


@router.delete("/unsubscribe")
async def unsubscribe(
    data: UnsubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Remove a push subscription."""
    db.query(PushSubscription).filter_by(
        endpoint=data.endpoint,
        user_id=current_user.id,
    ).delete()
    db.commit()
    return {"status": "unsubscribed"}
