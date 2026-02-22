import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core import events
from app.models.dm_channel import DirectMessageChannel
from app.models.server_membership import ServerMembership
from app.models.user import User
from app.redis import presence as presence_mgr
from app.services import auth_service
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


async def _ws_close(websocket: WebSocket, code: int = 1008) -> None:
    """Close a WebSocket, ignoring errors if it already closed."""
    try:
        await websocket.close(code=code)
    except (RuntimeError, Exception):
        pass


async def _authenticate(websocket: WebSocket, db: Session) -> User | None:
    """Accept the socket and expect the first message to be
    {"type": "auth", "token": "<jwt>"}.
    Returns the authenticated User or None on failure.
    """
    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        data = json.loads(raw)
    except WebSocketDisconnect:
        return None
    except Exception:
        await _ws_close(websocket)
        return None

    if data.get("type") != "auth":
        await _ws_close(websocket)
        return None

    token = data.get("token", "")
    user = auth_service.get_user_from_token(token, db)
    if not user:
        await _ws_close(websocket)
        return None

    return user


async def server_ws_handler(websocket: WebSocket, server_id: int, db: Session) -> None:
    """Full lifecycle handler for a server-level WebSocket connection.

    Handles text channels, typing indicators, and presence for a single server.
    Voice signaling is still routed through this connection — payloads include
    channel_id so the frontend can route them to the correct channel room.
    """
    user = await _authenticate(websocket, db)
    if user is None:
        return

    # Verify membership before accepting the connection
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

    await manager.connect(websocket, server_id, user.id)
    await presence_mgr.set_online(user.id)

    await manager.broadcast_to_server(
        server_id,
        {
            "type": events.USER_JOINED,
            "user_id": user.id,
            "username": user.username,
        },
    )
    await manager.broadcast_to_server(
        server_id,
        {
            "type": events.PRESENCE_CHANGED,
            "user_id": user.id,
            "status": "online",
        },
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
                    # Typing events include channel_id so the frontend
                    # shows the indicator only in the correct channel.
                    await manager.broadcast_to_server(
                        server_id,
                        {
                            "type": events.USER_TYPING,
                            "channel_id": data.get("channel_id"),
                            "user_id": user.id,
                            "username": user.username,
                        },
                        exclude_user_id=user.id,
                    )
                elif event_type == "presence.heartbeat":
                    await presence_mgr.heartbeat(user.id)

            except Exception as exc:
                logger.error(
                    "Error handling event %r from user %s: %s",
                    event_type,
                    user.id,
                    exc,
                    exc_info=True,
                )

    except WebSocketDisconnect:
        manager.disconnect(user.id, server_id)
        await presence_mgr.set_offline(user.id)
        await manager.broadcast_to_server(
            server_id,
            {
                "type": events.USER_LEFT,
                "user_id": user.id,
                "username": user.username,
            },
        )
        await manager.broadcast_to_server(
            server_id,
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

    dm = db.query(DirectMessageChannel).filter(DirectMessageChannel.id == dm_id).first()
    if not dm or user.id not in (dm.user1_id, dm.user2_id):
        await _ws_close(websocket, code=1008)
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
                    {
                        "type": events.USER_TYPING,
                        "user_id": user.id,
                        "username": user.username,
                    },
                )
            elif event_type == "presence.heartbeat":
                await presence_mgr.heartbeat(user.id)

    except WebSocketDisconnect:
        manager.disconnect_dm(user.id, dm_id)
        await presence_mgr.set_offline(user.id)
