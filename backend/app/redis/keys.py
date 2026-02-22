"""
Namespaced Redis key helpers.

Keys that are scoped to a logical server use the pattern:
  server:{server_id}:<type>:<entity_id>

Presence is not server-scoped because a user is online/offline globally
(they only open one connection per server, but their presence status is
visible deployment-wide, e.g. in DMs).

Non-server-scoped keys (DMs, global presence) are still prefixed with
SERVER_DOMAIN to avoid collisions when multiple deployments share a
Redis cluster.
"""

from app.config import settings

# ── Presence (global, not server-scoped) ────────────────────────────────────


def presence_key(user_id: int) -> str:
    return f"{settings.SERVER_DOMAIN}:presence:{user_id}"


# ── Voice (channel-scoped — voice rooms are channels, not servers) ───────────


def voice_user_key(user_id: int) -> str:
    return f"{settings.SERVER_DOMAIN}:voice:user:{user_id}"


def voice_channel_key(channel_id: int) -> str:
    return f"{settings.SERVER_DOMAIN}:voice:{channel_id}:users"


# ── Typing (server + channel scoped) ─────────────────────────────────────────


def typing_key(server_id: int, channel_id: int) -> str:
    return f"server:{server_id}:typing:{channel_id}"


# ── Pub/sub channels (server + channel scoped) ────────────────────────────────


def channel_pubsub_key(server_id: int, channel_id: int) -> str:
    return f"server:{server_id}:channel:{channel_id}"


# ── DMs (not server-scoped) ──────────────────────────────────────────────────


def dm_pubsub_key(dm_channel_id: int) -> str:
    return f"{settings.SERVER_DOMAIN}:dm:{dm_channel_id}"
