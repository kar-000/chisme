"""
Voice state manager — tracks who is in a voice channel in Redis.

Key scheme:
  voice:{channel_id}:users   →  Redis set of user_id strings
  voice:user:{user_id}       →  JSON blob with mute/video/channel state
  TTL = REDIS_PRESENCE_TTL seconds (default 300 s).

If Redis is unavailable every call is a no-op and queries return empty data.
"""

import json
import logging
from typing import Dict, List, Optional

from app.config import settings
from app.redis.client import get_redis

logger = logging.getLogger(__name__)

def _chan_key(channel_id: int) -> str:
    return f"voice:{channel_id}:users"


def _user_key(user_id: int) -> str:
    return f"voice:user:{user_id}"


async def join_voice(channel_id: int, user_id: int, muted: bool = False, video: bool = False) -> None:
    """Add a user to a voice channel and store their state."""
    r = get_redis()
    if r is None:
        return
    try:
        pipe = r.pipeline()
        pipe.sadd(_chan_key(channel_id), str(user_id))
        pipe.expire(_chan_key(channel_id), settings.REDIS_PRESENCE_TTL)
        state = json.dumps({"channel_id": channel_id, "muted": muted, "video": video})
        pipe.setex(_user_key(user_id), settings.REDIS_PRESENCE_TTL, state)
        await pipe.execute()
    except Exception as exc:
        logger.warning("voice.join_voice failed: %s", exc)


async def leave_voice(channel_id: int, user_id: int) -> None:
    """Remove a user from a voice channel."""
    r = get_redis()
    if r is None:
        return
    try:
        pipe = r.pipeline()
        pipe.srem(_chan_key(channel_id), str(user_id))
        pipe.delete(_user_key(user_id))
        await pipe.execute()
    except Exception as exc:
        logger.warning("voice.leave_voice failed: %s", exc)


async def update_state(user_id: int, channel_id: int, muted: bool, video: bool) -> None:
    """Update mute/video state for an already-joined user."""
    r = get_redis()
    if r is None:
        return
    try:
        state = json.dumps({"channel_id": channel_id, "muted": muted, "video": video})
        await r.setex(_user_key(user_id), settings.REDIS_PRESENCE_TTL, state)
    except Exception as exc:
        logger.warning("voice.update_state failed: %s", exc)


async def heartbeat(channel_id: int, user_id: int) -> None:
    """Refresh TTL for both the channel set and the user state key."""
    r = get_redis()
    if r is None:
        return
    try:
        pipe = r.pipeline()
        pipe.expire(_chan_key(channel_id), settings.REDIS_PRESENCE_TTL)
        pipe.expire(_user_key(user_id), settings.REDIS_PRESENCE_TTL)
        await pipe.execute()
    except Exception as exc:
        logger.warning("voice.heartbeat failed: %s", exc)


async def get_channel_voice_users(channel_id: int) -> List[int]:
    """Return list of user_ids currently in a voice channel."""
    r = get_redis()
    if r is None:
        return []
    try:
        members = await r.smembers(_chan_key(channel_id))
        return [int(uid) for uid in members]
    except Exception as exc:
        logger.warning("voice.get_channel_voice_users failed: %s", exc)
        return []


async def get_user_voice_state(user_id: int) -> Optional[dict]:
    """Return the voice state dict for a user, or None if not in voice."""
    r = get_redis()
    if r is None:
        return None
    try:
        raw = await r.get(_user_key(user_id))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("voice.get_user_voice_state failed: %s", exc)
        return None


async def get_bulk_voice_states(user_ids: List[int]) -> Dict[int, Optional[dict]]:
    """Return {user_id: state_dict_or_None} for multiple users via pipeline."""
    if not user_ids:
        return {}
    r = get_redis()
    if r is None:
        return {uid: None for uid in user_ids}
    try:
        pipe = r.pipeline()
        for uid in user_ids:
            pipe.get(_user_key(uid))
        values = await pipe.execute()
        result: Dict[int, Optional[dict]] = {}
        for uid, raw in zip(user_ids, values):
            result[uid] = json.loads(raw) if raw else None
        return result
    except Exception as exc:
        logger.warning("voice.get_bulk_voice_states failed: %s", exc)
        return {uid: None for uid in user_ids}
