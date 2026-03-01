"""Per-server voice channel WebSocket handler.

Each server has its own isolated voice channel.  Users in Server A's voice
call cannot see or signal users in Server B's voice call.

The endpoint is /ws/voice/{server_id} — the server_id is taken from the URL
path and validated against the user's server membership before the connection
is accepted.

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
from app.models.server_membership import ServerMembership
from app.websocket.handlers import _authenticate, _ws_close

logger = logging.getLogger(__name__)


class VoiceConnectionManager:
    """Tracks voice WebSocket connections and voice user state, scoped per server."""

    def __init__(self) -> None:
        # server_id -> {user_id -> WebSocket}
        self._connections: dict[int, dict[int, WebSocket]] = {}
        # server_id -> {user_id -> {user_id, username, muted, video, speaking}}
        self._voice_users: dict[int, dict[int, dict]] = {}
        # server_id -> {user_id -> pending leave task (7-second grace period)}
        self._pending_leaves: dict[int, dict[int, asyncio.Task]] = {}

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self, server_id: int, user_id: int, websocket: WebSocket) -> None:
        server_conns = self._connections.setdefault(server_id, {})
        # Close any stale connection for this user in this server before replacing it
        old = server_conns.get(user_id)
        if old is not None:
            try:
                await old.close()
            except Exception:
                pass
        server_conns[user_id] = websocket

    def disconnect(self, server_id: int, user_id: int) -> None:
        server_conns = self._connections.get(server_id)
        if server_conns is not None:
            server_conns.pop(user_id, None)
            if not server_conns:
                self._connections.pop(server_id, None)

    # ------------------------------------------------------------------
    # Voice state
    # ------------------------------------------------------------------

    def join_voice(self, server_id: int, user_id: int, username: str, muted: bool, video: bool) -> None:
        self._voice_users.setdefault(server_id, {})[user_id] = {
            "user_id": user_id,
            "username": username,
            "muted": muted,
            "video": video,
            "speaking": False,
        }

    def leave_voice(self, server_id: int, user_id: int) -> bool:
        server_voice = self._voice_users.get(server_id)
        if server_voice is None:
            return False
        existed = server_voice.pop(user_id, None) is not None
        if not server_voice:
            self._voice_users.pop(server_id, None)
        return existed

    def update_voice(self, server_id: int, user_id: int, muted: bool, video: bool, speaking: bool) -> None:
        state = self._voice_users.get(server_id, {}).get(user_id)
        if state:
            state["muted"] = muted
            state["video"] = video
            state["speaking"] = speaking

    def is_in_voice(self, server_id: int, user_id: int) -> bool:
        return user_id in self._voice_users.get(server_id, {})

    def get_snapshot(self, server_id: int) -> list[dict]:
        return list(self._voice_users.get(server_id, {}).values())

    # ------------------------------------------------------------------
    # Reconnection grace period
    # ------------------------------------------------------------------

    async def schedule_leave(self, server_id: int, user_id: int, delay: float = 7.0) -> None:
        """Broadcast user_left after `delay` seconds unless cancel_leave() is called first."""
        server_leaves = self._pending_leaves.setdefault(server_id, {})
        existing = server_leaves.pop(user_id, None)
        if existing:
            existing.cancel()

        async def _delayed() -> None:
            await asyncio.sleep(delay)
            if self.leave_voice(server_id, user_id):
                await self.broadcast(
                    server_id,
                    {
                        "type": events.VOICE_USER_LEFT,
                        "channel_id": server_id,
                        "user_id": user_id,
                    },
                )
            self._pending_leaves.get(server_id, {}).pop(user_id, None)

        server_leaves[user_id] = asyncio.create_task(_delayed())

    def cancel_leave(self, server_id: int, user_id: int) -> None:
        """Cancel a pending delayed leave (user reconnected in time)."""
        task = self._pending_leaves.get(server_id, {}).pop(user_id, None)
        if task:
            task.cancel()

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def broadcast(self, server_id: int, payload: dict, exclude: int | None = None) -> None:
        """Send to all voice WS clients connected to this server."""
        data = json.dumps(payload)
        dead: list[int] = []
        for uid, ws in list(self._connections.get(server_id, {}).items()):
            if uid == exclude:
                continue
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(server_id, uid)

    async def send_to(self, server_id: int, user_id: int, payload: dict) -> None:
        """Send to a specific connected user within a server."""
        ws = self._connections.get(server_id, {}).get(user_id)
        if ws is None:
            return
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            self.disconnect(server_id, user_id)


# Module-level singleton — shared across all connections (single-process only)
voice_manager = VoiceConnectionManager()


async def voice_ws_handler(websocket: WebSocket, server_id: int, db: Session) -> None:
    """Full lifecycle handler for the per-server /ws/voice/{server_id} endpoint."""
    # Reuse the shared auth helper (accepts + verifies the JWT handshake)
    user = await _authenticate(websocket, db)
    if user is None:
        return

    # Verify the user is a member of this server before accepting voice connection
    membership = (
        db.query(ServerMembership)
        .filter(
            ServerMembership.server_id == server_id,
            ServerMembership.user_id == user.id,
        )
        .first()
    )
    if not membership:
        await _ws_close(websocket, code=4003)
        return

    await voice_manager.connect(server_id, user.id, websocket)
    # Cancel any pending grace-period leave from a previous disconnect
    voice_manager.cancel_leave(server_id, user.id)

    # Send the current participant list to the newly connected client so it
    # can clear any stale state from a previous session.
    await websocket.send_text(
        json.dumps(
            {
                "type": events.VOICE_STATE_SNAPSHOT,
                "channel_id": server_id,
                "users": voice_manager.get_snapshot(server_id),
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
                    voice_manager.join_voice(server_id, user.id, user.username, muted, video)
                    await voice_manager.broadcast(
                        server_id,
                        {
                            "type": events.VOICE_USER_JOINED,
                            "channel_id": server_id,
                            "user_id": user.id,
                            "username": user.username,
                            "muted": muted,
                            "video": video,
                        },
                    )

                elif msg_type == events.VOICE_LEAVE:
                    voice_manager.leave_voice(server_id, user.id)
                    await voice_manager.broadcast(
                        server_id,
                        {
                            "type": events.VOICE_USER_LEFT,
                            "channel_id": server_id,
                            "user_id": user.id,
                        },
                    )

                elif msg_type == events.VOICE_STATE_UPDATE:
                    muted = bool(msg.get("muted", True))
                    video = bool(msg.get("video", False))
                    speaking = bool(msg.get("speaking", False))
                    voice_manager.update_voice(server_id, user.id, muted, video, speaking)
                    await voice_manager.broadcast(
                        server_id,
                        {
                            "type": events.VOICE_STATE_CHANGED,
                            "channel_id": server_id,
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
                    if not voice_manager.is_in_voice(server_id, target_id):
                        continue
                    await voice_manager.send_to(
                        server_id,
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
                    if not voice_manager.is_in_voice(server_id, target_id):
                        continue
                    await voice_manager.send_to(
                        server_id,
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
        was_in_voice = voice_manager.is_in_voice(server_id, user.id)
        voice_manager.disconnect(server_id, user.id)
        if was_in_voice:
            # Broadcast reconnecting state; schedule actual leave after grace period.
            # If the user reconnects within 7 seconds, cancel_leave() clears the task.
            await voice_manager.broadcast(
                server_id,
                {
                    "type": events.VOICE_USER_RECONNECTING,
                    "channel_id": server_id,
                    "user_id": user.id,
                },
            )
            await voice_manager.schedule_leave(server_id, user.id, delay=7.0)
