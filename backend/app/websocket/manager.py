import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per channel and DM channel.

    Connections are stored as {room_id: {user_id: WebSocket}} so that
    voice signaling messages (offer/answer/ICE) can be routed to a
    specific peer without broadcasting to everyone.
    """

    def __init__(self) -> None:
        # channel_id -> {user_id: WebSocket}
        self._connections: dict[int, dict[int, WebSocket]] = defaultdict(dict)
        # dm_channel_id -> {user_id: WebSocket}
        self._dm_connections: dict[int, dict[int, WebSocket]] = defaultdict(dict)
        # channel_id -> {user_id: {user_id, username, muted, video}}
        # In-memory voice state — no Redis dependency for presence snapshots.
        self._voice_users: dict[int, dict[int, dict]] = defaultdict(dict)

    # ------------------------------------------------------------------
    # Channel connections
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket, channel_id: int, user_id: int) -> None:
        self._connections[channel_id][user_id] = websocket
        logger.info("WebSocket connected to channel %s (user %s)", channel_id, user_id)

    def disconnect(self, user_id: int, channel_id: int) -> None:
        self._connections.get(channel_id, {}).pop(user_id, None)
        logger.info("WebSocket disconnected from channel %s (user %s)", channel_id, user_id)

    async def broadcast(self, channel_id: int, payload: dict) -> None:
        """Broadcast a JSON payload to all connections in a channel."""
        dead: list[int] = []
        for uid, ws in list(self._connections.get(channel_id, {}).items()):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(uid, channel_id)

    async def send_to_user(self, channel_id: int, user_id: int, payload: dict) -> bool:
        """Send a JSON payload to a specific user in a channel.

        Returns True if delivered, False if the user isn't connected here.
        """
        ws = self._connections.get(channel_id, {}).get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_text(json.dumps(payload))
            return True
        except Exception:
            self.disconnect(user_id, channel_id)
            return False

    def get_channel_users(self, channel_id: int) -> list[int]:
        """Return user_ids currently connected to a channel."""
        return list(self._connections.get(channel_id, {}).keys())

    # ------------------------------------------------------------------
    # In-memory voice state
    # ------------------------------------------------------------------

    def voice_user_join(self, channel_id: int, user_id: int, username: str, muted: bool, video: bool) -> None:
        self._voice_users[channel_id][user_id] = {
            "user_id": user_id,
            "username": username,
            "muted": muted,
            "video": video,
        }

    def voice_user_leave(self, channel_id: int, user_id: int) -> None:
        self._voice_users.get(channel_id, {}).pop(user_id, None)

    def voice_user_update(self, channel_id: int, user_id: int, muted: bool, video: bool) -> None:
        state = self._voice_users.get(channel_id, {}).get(user_id)
        if state:
            state["muted"] = muted
            state["video"] = video

    def get_voice_users(self, channel_id: int) -> list[dict]:
        """Return all voice user state dicts for a channel."""
        return list(self._voice_users.get(channel_id, {}).values())

    def is_in_voice(self, channel_id: int, user_id: int) -> bool:
        return user_id in self._voice_users.get(channel_id, {})

    # ------------------------------------------------------------------
    # DM connections
    # ------------------------------------------------------------------

    async def connect_dm(self, websocket: WebSocket, dm_id: int, user_id: int) -> None:
        self._dm_connections[dm_id][user_id] = websocket
        logger.info("WebSocket connected to DM channel %s (user %s)", dm_id, user_id)

    def disconnect_dm(self, user_id: int, dm_id: int) -> None:
        self._dm_connections.get(dm_id, {}).pop(user_id, None)
        logger.info("WebSocket disconnected from DM channel %s (user %s)", dm_id, user_id)

    async def broadcast_dm(self, dm_id: int, payload: dict) -> None:
        """Broadcast a JSON payload to all connections in a DM channel."""
        dead: list[int] = []
        for uid, ws in list(self._dm_connections.get(dm_id, {}).items()):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect_dm(uid, dm_id)

    async def send_personal(self, websocket: WebSocket, payload: dict) -> None:
        await websocket.send_text(json.dumps(payload))


manager = ConnectionManager()
