"""
Web Push delivery service.

Uses pywebpush to send push notifications to subscribed browsers.
Automatically removes subscriptions that return HTTP 410 (expired/revoked).
"""

import json
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


def send_push_to_user(
    *,
    user_id: int,
    title: str,
    body: str,
    url: str,
    tag: str,
    db: Session,
) -> None:
    """Send a push notification to every registered device for a user.

    Silently skips if VAPID keys are not configured.
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return  # Push not configured — skip silently

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("pywebpush not installed — push notifications disabled")
        return

    subscriptions = db.query(PushSubscription).filter_by(user_id=user_id).all()

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"title": title, "body": body, "url": url, "tag": tag}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL},
            )
        except WebPushException as exc:
            if exc.response is not None and exc.response.status_code == 410:
                logger.info("Removing expired push subscription %s for user %s", sub.id, user_id)
                db.delete(sub)
                db.commit()
            else:
                logger.warning("Push delivery failed for subscription %s: %s", sub.id, exc)
        except Exception as exc:
            logger.warning("Unexpected push error for subscription %s: %s", sub.id, exc)
