import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core import events
from app.core.security import decode_access_token
from app.models.user import User
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


async def _authenticate(websocket: WebSocket, db: Session) -> User | None:
    """Expect the first message to be {"type": "auth", "token": "<jwt>"}."""
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
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()  # noqa: E712
    if not user:
        await websocket.close(code=1008)
        return None

    return user


async def channel_ws_handler(websocket: WebSocket, channel_id: int, db: Session) -> None:
    """Full lifecycle handler for a channel WebSocket connection."""
    user = await _authenticate(websocket, db)
    if user is None:
        return

    await manager.connect(websocket, channel_id)
    # Announce join
    await manager.broadcast(
        channel_id,
        {"type": events.USER_JOINED, "user_id": user.id, "username": user.username},
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = data.get("type")

            if event_type == events.USER_TYPING:
                await manager.broadcast(
                    channel_id,
                    {"type": events.USER_TYPING, "user_id": user.id, "username": user.username},
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, channel_id)
        await manager.broadcast(
            channel_id,
            {"type": events.USER_LEFT, "user_id": user.id, "username": user.username},
        )
