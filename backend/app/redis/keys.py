"""
Namespaced Redis key helpers.

All keys are prefixed with settings.SERVER_DOMAIN so that multiple independent
Chisme deployments sharing a Redis cluster never collide. For single-instance
deployments this is also good hygiene and makes MONITOR output readable.
"""

from app.config import settings


def presence_key(user_id: int) -> str:
    return f"{settings.SERVER_DOMAIN}:presence:{user_id}"


def voice_user_key(user_id: int) -> str:
    return f"{settings.SERVER_DOMAIN}:voice:user:{user_id}"


def voice_channel_key(channel_id: int) -> str:
    return f"{settings.SERVER_DOMAIN}:voice:{channel_id}:users"
