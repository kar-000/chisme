"""Global voice channel WebSocket handler.

A single /ws/voice endpoint serves the entire server — voice state is
not tied to any text channel.  All connected clients receive all voice
events, and P2P signaling (offer/answer/ICE) is relayed directly between
voice participants without knowing which text channel they are viewing.
"""

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core import events
from app.services import auth_service

logger = logging.getLogger(__name__)

# Sentinel value kept for protocol compatibility (voice.state_snapshot includes
# channel_id; 0 signals "global / server-wide").
GLOBAL_VOICE_CHANNEL = 0


class VoiceConnectionManager:
    """Tracks voice WebSocket connections and voice user state globally."""

    def __init__(self) -> None:
        # user_id -> WebSocket
        self._connections: dict[int, WebSocket] = {}
        # user_id -> {user_id, username, muted, video, speaking}
        self._voice_users: dict[int, dict] = {}

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        # Close any stale connection for this user before replacing it
        old = self._connections.get(user_id)
        if old is not None:
            try:
                await old.close()
            except Exception:
                pass
        self._connections[user_id] = websocket

    def disconnect(self, user_id: int) -> None:
        self._connections.pop(user_id, None)

    # ------------------------------------------------------------------
    # Voice state
    # ------------------------------------------------------------------

    def join_voice(self, user_id: int, username: str, muted: bool, video: bool) -> None:
        self._voice_users[user_id] = {
            "user_id": user_id,
            "username": username,
            "muted": muted,
            "video": video,
            "speaking": False,
        }

    def leave_voice(self, user_id: int) -> bool:
        return self._voice_users.pop(user_id, None) is not None

    def update_voice(self, user_id: int, muted: bool, video: bool, speaking: bool) -> None:
        state = self._voice_users.get(user_id)
        if state:
            state["muted"] = muted
            state["video"] = video
            state["speaking"] = speaking

    def is_in_voice(self, user_id: int) -> bool:
        return user_id in self._voice_users

    def get_snapshot(self) -> list[dict]:
        return list(self._voice_users.values())

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def broadcast(self, payload: dict, exclude: int | None = None) -> None:
        """Send to all connected voice WS clients."""
        data = json.dumps(payload)
        dead: list[int] = []
        for uid, ws in list(self._connections.items()):
            if uid == exclude:
                continue
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(uid)

    async def send_to(self, user_id: int, payload: dict) -> None:
        """Send to a specific connected user."""
        ws = self._connections.get(user_id)
        if ws is None:
            return
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            self.disconnect(user_id)


# Module-level singleton — shared across all connections
voice_manager = VoiceConnectionManager()


async def voice_ws_handler(websocket: WebSocket, db: Session) -> None:
    """Full lifecycle handler for the global /ws/voice endpoint."""
    await websocket.accept()
    user = None
    try:
        # ── Auth handshake ─────────────────────────────────────────────
        try:
            raw = await websocket.receive_text()
            data = json.loads(raw)
        except (WebSocketDisconnect, Exception):
            await websocket.close(code=1008)
            return

        if data.get("type") != "auth":
            await websocket.close(code=1008)
            return

        user = auth_service.get_user_from_token(data.get("token", ""), db)
        if not user:
            await websocket.close(code=1008)
            return

        await voice_manager.connect(user.id, websocket)

        # Send current voice participants to the new connection
        await websocket.send_text(
            json.dumps(
                {
                    "type": events.VOICE_STATE_SNAPSHOT,
                    "channel_id": GLOBAL_VOICE_CHANNEL,
                    "users": voice_manager.get_snapshot(),
                }
            )
        )

        # ── Message loop ───────────────────────────────────────────────
        while True:
            raw = await websocket.receive_text()
            try:
                msg: dict = json.loads(raw)
            except Exception:
                continue

            msg_type = msg.get("type")

            try:
                if msg_type == events.VOICE_JOIN:
                    muted = bool(msg.get("muted", True))
                    video = bool(msg.get("video", False))
                    voice_manager.join_voice(user.id, user.username, muted, video)
                    await voice_manager.broadcast(
                        {
                            "type": events.VOICE_USER_JOINED,
                            "channel_id": GLOBAL_VOICE_CHANNEL,
                            "user_id": user.id,
                            "username": user.username,
                            "muted": muted,
                            "video": video,
                        }
                    )

                elif msg_type == events.VOICE_LEAVE:
                    voice_manager.leave_voice(user.id)
                    await voice_manager.broadcast(
                        {
                            "type": events.VOICE_USER_LEFT,
                            "channel_id": GLOBAL_VOICE_CHANNEL,
                            "user_id": user.id,
                        }
                    )

                elif msg_type == events.VOICE_STATE_UPDATE:
                    muted = bool(msg.get("muted", True))
                    video = bool(msg.get("video", False))
                    speaking = bool(msg.get("speaking", False))
                    voice_manager.update_voice(user.id, muted, video, speaking)
                    await voice_manager.broadcast(
                        {
                            "type": events.VOICE_STATE_CHANGED,
                            "channel_id": GLOBAL_VOICE_CHANNEL,
                            "user_id": user.id,
                            "muted": muted,
                            "video": video,
                            "speaking": speaking,
                        },
                        exclude=user.id,
                    )

                elif msg_type in (events.VOICE_OFFER, events.VOICE_ANSWER, events.VOICE_ICE_CANDIDATE):
                    target_id = msg.get("target_user_id")
                    if not isinstance(target_id, int):
                        continue
                    if not voice_manager.is_in_voice(target_id):
                        continue
                    relay = {k: v for k, v in msg.items() if k != "target_user_id"}
                    relay["from_user_id"] = user.id
                    await voice_manager.send_to(target_id, relay)

                elif msg_type == events.VOICE_HEARTBEAT:
                    pass  # keepalive — no action needed

            except Exception as exc:
                logger.error(
                    "voice_ws_handler: error handling %r from user %s: %s",
                    msg_type,
                    user.id,
                    exc,
                    exc_info=True,
                )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("voice_ws_handler: unexpected error: %s", exc)
    finally:
        if user is not None:
            was_in_voice = voice_manager.is_in_voice(user.id)
            voice_manager.leave_voice(user.id)
            voice_manager.disconnect(user.id)
            if was_in_voice:
                await voice_manager.broadcast(
                    {
                        "type": events.VOICE_USER_LEFT,
                        "channel_id": GLOBAL_VOICE_CHANNEL,
                        "user_id": user.id,
                    }
                )
