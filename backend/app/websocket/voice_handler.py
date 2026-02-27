"""Global voice channel WebSocket handler.

A single /ws/voice endpoint serves the entire server — voice state is
not tied to any text channel.  All connected clients receive all voice
events, and P2P signaling (offer/answer/ICE) is relayed directly between
voice participants without knowing which text channel they are viewing.

NOTE: VoiceConnectionManager is an in-memory singleton, matching the same
design as ConnectionManager in manager.py.  Both assume a single-process
deployment (single uvicorn worker).  A Redis-backed implementation would
be required for multi-worker/multi-node setups.
"""

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core import events
from app.websocket.handlers import _authenticate

logger = logging.getLogger(__name__)

# channel_id value included in voice protocol messages.
# 0 signals "global / server-wide" — there is no corresponding DB row.
GLOBAL_VOICE_CHANNEL = 0


class VoiceConnectionManager:
    """Tracks voice WebSocket connections and voice user state globally."""

    def __init__(self) -> None:
        # user_id -> WebSocket
        self._connections: dict[int, WebSocket] = {}
        # user_id -> {user_id, username, muted, video, speaking}
        self._voice_users: dict[int, dict] = {}
        # user_id -> pending leave task (7-second grace period)
        self._pending_leaves: dict[int, asyncio.Task] = {}

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
    # Reconnection grace period
    # ------------------------------------------------------------------

    async def schedule_leave(self, user_id: int, delay: float = 7.0) -> None:
        """Broadcast user_left after `delay` seconds unless cancel_leave() is called first."""
        existing = self._pending_leaves.pop(user_id, None)
        if existing:
            existing.cancel()

        async def _delayed() -> None:
            await asyncio.sleep(delay)
            if self.leave_voice(user_id):
                await self.broadcast(
                    {
                        "type": events.VOICE_USER_LEFT,
                        "channel_id": GLOBAL_VOICE_CHANNEL,
                        "user_id": user_id,
                    }
                )
            self._pending_leaves.pop(user_id, None)

        self._pending_leaves[user_id] = asyncio.create_task(_delayed())

    def cancel_leave(self, user_id: int) -> None:
        """Cancel a pending delayed leave (user reconnected in time)."""
        task = self._pending_leaves.pop(user_id, None)
        if task:
            task.cancel()

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


# Module-level singleton — shared across all connections (single-process only)
voice_manager = VoiceConnectionManager()


async def voice_ws_handler(websocket: WebSocket, db: Session) -> None:
    """Full lifecycle handler for the global /ws/voice endpoint."""
    # Reuse the shared auth helper (accepts + verifies the JWT handshake)
    user = await _authenticate(websocket, db)
    if user is None:
        return

    await voice_manager.connect(user.id, websocket)
    # Cancel any pending grace-period leave from a previous disconnect
    voice_manager.cancel_leave(user.id)

    # Send the current participant list to the newly connected client so it
    # can clear any stale state from a previous session.
    await websocket.send_text(
        json.dumps(
            {
                "type": events.VOICE_STATE_SNAPSHOT,
                "channel_id": GLOBAL_VOICE_CHANNEL,
                "users": voice_manager.get_snapshot(),
            }
        )
    )

    try:
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

                elif msg_type in (events.VOICE_OFFER, events.VOICE_ANSWER):
                    target_id = msg.get("target_user_id")
                    if not isinstance(target_id, int):
                        continue
                    if not voice_manager.is_in_voice(target_id):
                        continue
                    await voice_manager.send_to(
                        target_id,
                        {
                            "type": msg_type,
                            "from_user_id": user.id,
                            "sdp": msg.get("sdp"),
                        },
                    )

                elif msg_type == events.VOICE_ICE_CANDIDATE:
                    target_id = msg.get("target_user_id")
                    if not isinstance(target_id, int):
                        continue
                    if not voice_manager.is_in_voice(target_id):
                        continue
                    await voice_manager.send_to(
                        target_id,
                        {
                            "type": msg_type,
                            "from_user_id": user.id,
                            "candidate": msg.get("candidate"),
                        },
                    )

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
        was_in_voice = voice_manager.is_in_voice(user.id)
        voice_manager.disconnect(user.id)
        if was_in_voice:
            # Broadcast reconnecting state; schedule actual leave after grace period.
            # If the user reconnects within 7 seconds, cancel_leave() clears the task.
            await voice_manager.broadcast(
                {
                    "type": events.VOICE_USER_RECONNECTING,
                    "channel_id": GLOBAL_VOICE_CHANNEL,
                    "user_id": user.id,
                }
            )
            await voice_manager.schedule_leave(user.id, delay=7.0)
