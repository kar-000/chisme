"""
Presence manager — tracks online/away/dnd status in Redis.

Key scheme:
  presence:{user_id}  →  "online" | "away" | "dnd"
  TTL = REDIS_PRESENCE_TTL seconds (default 300 s).

If Redis is unavailable every call is a no-op and get_status returns "offline".
"""

import logging
from typing import Dict, List

from app.config import settings
from app.redis.client import get_redis

logger = logging.getLogger(__name__)

_PREFIX = "presence"
VALID_STATUSES = {"online", "away", "dnd"}


def _key(user_id: int) -> str:
    return f"{_PREFIX}:{user_id}"


async def set_online(user_id: int, status: str = "online") -> None:
    """Mark a user as online (or away/dnd) with a TTL-based expiry."""
    if status not in VALID_STATUSES:
        logger.warning("presence.set_online: invalid status %r — ignoring", status)
        return
    r = get_redis()
    if r is None:
        return
    try:
        await r.setex(_key(user_id), settings.REDIS_PRESENCE_TTL, status)
    except Exception as exc:
        logger.warning("presence.set_online failed: %s", exc)


async def set_offline(user_id: int) -> None:
    """Immediately mark a user as offline by deleting their key."""
    r = get_redis()
    if r is None:
        return
    try:
        await r.delete(_key(user_id))
    except Exception as exc:
        logger.warning("presence.set_offline failed: %s", exc)


async def heartbeat(user_id: int) -> None:
    """Refresh the TTL without changing the status value."""
    r = get_redis()
    if r is None:
        return
    try:
        await r.expire(_key(user_id), settings.REDIS_PRESENCE_TTL)
    except Exception as exc:
        logger.warning("presence.heartbeat failed: %s", exc)


async def get_status(user_id: int) -> str:
    """Return the current status string, or 'offline' if not set / Redis down."""
    r = get_redis()
    if r is None:
        return "offline"
    try:
        value = await r.get(_key(user_id))
        return value if value else "offline"
    except Exception as exc:
        logger.warning("presence.get_status failed: %s", exc)
        return "offline"


async def get_bulk_status(user_ids: List[int]) -> Dict[int, str]:
    """Return {user_id: status} for multiple users in a single pipeline."""
    if not user_ids:
        return {}
    r = get_redis()
    if r is None:
        return {uid: "offline" for uid in user_ids}
    try:
        pipe = r.pipeline()
        for uid in user_ids:
            pipe.get(_key(uid))
        values = await pipe.execute()
        return {uid: (v if v else "offline") for uid, v in zip(user_ids, values)}
    except Exception as exc:
        logger.warning("presence.get_bulk_status failed: %s", exc)
        return {uid: "offline" for uid in user_ids}
