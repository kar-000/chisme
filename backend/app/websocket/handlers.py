import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core import events
from app.core.security import decode_access_token
from app.models.dm_channel import DirectMessageChannel
from app.models.user import User
from app.redis import presence as presence_mgr
from app.redis import voice as voice_mgr
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


async def _authenticate(websocket: WebSocket, db: Session) -> User | None:
    """Expect the first message to be {"type": "auth", "token": "<jwt>"}."""
    await websocket.accept()  # must accept before receive_text()
    try:
        raw = await websocket.receive_text()
        data = json.loads(raw)
    except Exception:
        await websocket.close(code=1008)
        return None

    if data.get("type") != "auth":
        await websocket.close(code=1008)
        return None

    token = data.get("token", "")
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=1008)
        return None

    user_id = payload.get("sub")
    try:
        user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()  # noqa: E712
    except (TypeError, ValueError):
        await websocket.close(code=1008)
        return None
    if not user:
        await websocket.close(code=1008)
        return None

    return user


async def channel_ws_handler(websocket: WebSocket, channel_id: int, db: Session) -> None:
    """Full lifecycle handler for a channel WebSocket connection."""
    user = await _authenticate(websocket, db)
    if user is None:
        return

    await manager.connect(websocket, channel_id, user.id)
    await presence_mgr.set_online(user.id)
    # Announce join + presence
    await manager.broadcast(
        channel_id,
        {
            "type": events.USER_JOINED,
            "user_id": user.id,
            "username": user.username,
        },
    )
    await manager.broadcast(
        channel_id,
        {
            "type": events.PRESENCE_CHANGED,
            "user_id": user.id,
            "status": "online",
        },
    )

    # Send current voice channel occupants to the newly connected user
    voice_user_ids = await voice_mgr.get_channel_voice_users(channel_id)
    if voice_user_ids:
        voice_states = await voice_mgr.get_bulk_voice_states(voice_user_ids)
        users_in_voice = db.query(User).filter(User.id.in_(voice_user_ids)).all()
        username_map = {u.id: u.username for u in users_in_voice}
        snapshot = [
            {
                "user_id": uid,
                "username": username_map.get(uid, "unknown"),
                "muted": (state or {}).get("muted", True),
                "video": (state or {}).get("video", False),
            }
            for uid, state in voice_states.items()
            if state is not None
        ]
        if snapshot:
            await manager.send_to_user(
                channel_id,
                user.id,
                {"type": events.VOICE_STATE_SNAPSHOT, "channel_id": channel_id, "users": snapshot},
            )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = data.get("type")

            try:
                if event_type == events.USER_TYPING:
                    await manager.broadcast(
                        channel_id,
                        {"type": events.USER_TYPING, "user_id": user.id, "username": user.username},
                    )
                elif event_type == "presence.heartbeat":
                    await presence_mgr.heartbeat(user.id)

                # ------------------------------------------------------------------
                # Voice signaling
                # ------------------------------------------------------------------
                elif event_type == events.VOICE_JOIN:
                    muted = bool(data.get("muted", False))
                    video = bool(data.get("video", False))
                    await voice_mgr.join_voice(channel_id, user.id, muted=muted, video=video)
                    await manager.broadcast(
                        channel_id,
                        {
                            "type": events.VOICE_USER_JOINED,
                            "channel_id": channel_id,
                            "user_id": user.id,
                            "username": user.username,
                            "muted": muted,
                            "video": video,
                        },
                    )

                elif event_type == events.VOICE_LEAVE:
                    await voice_mgr.leave_voice(channel_id, user.id)
                    await manager.broadcast(
                        channel_id,
                        {
                            "type": events.VOICE_USER_LEFT,
                            "channel_id": channel_id,
                            "user_id": user.id,
                            "username": user.username,
                        },
                    )

                elif event_type == events.VOICE_STATE_UPDATE:
                    muted = bool(data.get("muted", False))
                    video = bool(data.get("video", False))
                    await voice_mgr.update_state(user.id, channel_id, muted=muted, video=video)
                    await manager.broadcast(
                        channel_id,
                        {
                            "type": events.VOICE_STATE_CHANGED,
                            "channel_id": channel_id,
                            "user_id": user.id,
                            "muted": muted,
                            "video": video,
                        },
                    )

                elif event_type == events.VOICE_OFFER:
                    target_id = data.get("target_user_id")
                    if target_id is not None:
                        await manager.send_to_user(
                            channel_id,
                            int(target_id),
                            {
                                "type": events.VOICE_OFFER,
                                "from_user_id": user.id,
                                "sdp": data.get("sdp"),
                            },
                        )

                elif event_type == events.VOICE_ANSWER:
                    target_id = data.get("target_user_id")
                    if target_id is not None:
                        await manager.send_to_user(
                            channel_id,
                            int(target_id),
                            {
                                "type": events.VOICE_ANSWER,
                                "from_user_id": user.id,
                                "sdp": data.get("sdp"),
                            },
                        )

                elif event_type == events.VOICE_ICE_CANDIDATE:
                    target_id = data.get("target_user_id")
                    if target_id is not None:
                        await manager.send_to_user(
                            channel_id,
                            int(target_id),
                            {
                                "type": events.VOICE_ICE_CANDIDATE,
                                "from_user_id": user.id,
                                "candidate": data.get("candidate"),
                            },
                        )

                elif event_type == "voice.heartbeat":
                    await voice_mgr.heartbeat(channel_id, user.id)

            except Exception as exc:
                logger.error("Error handling event %r from user %s: %s", event_type, user.id, exc, exc_info=True)

    except WebSocketDisconnect:
        # Auto-leave voice if connected
        voice_state = await voice_mgr.get_user_voice_state(user.id)
        if voice_state and voice_state.get("channel_id") == channel_id:
            await voice_mgr.leave_voice(channel_id, user.id)
            await manager.broadcast(
                channel_id,
                {
                    "type": events.VOICE_USER_LEFT,
                    "channel_id": channel_id,
                    "user_id": user.id,
                    "username": user.username,
                },
            )

        manager.disconnect(user.id, channel_id)
        await presence_mgr.set_offline(user.id)
        await manager.broadcast(
            channel_id,
            {"type": events.USER_LEFT, "user_id": user.id, "username": user.username},
        )
        await manager.broadcast(
            channel_id,
            {
                "type": events.PRESENCE_CHANGED,
                "user_id": user.id,
                "status": "offline",
            },
        )


async def dm_ws_handler(websocket: WebSocket, dm_id: int, db: Session) -> None:
    """Full lifecycle handler for a DM channel WebSocket connection."""
    user = await _authenticate(websocket, db)
    if user is None:
        return

    # Verify user is a participant of this DM channel
    dm = db.query(DirectMessageChannel).filter(DirectMessageChannel.id == dm_id).first()
    if not dm or user.id not in (dm.user1_id, dm.user2_id):
        await websocket.close(code=1008)
        return

    await manager.connect_dm(websocket, dm_id, user.id)
    await presence_mgr.set_online(user.id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = data.get("type")

            if event_type == events.USER_TYPING:
                await manager.broadcast_dm(
                    dm_id,
                    {"type": events.USER_TYPING, "user_id": user.id, "username": user.username},
                )
            elif event_type == "presence.heartbeat":
                await presence_mgr.heartbeat(user.id)

    except WebSocketDisconnect:
        manager.disconnect_dm(user.id, dm_id)
        await presence_mgr.set_offline(user.id)
