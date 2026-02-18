import json
import logging
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per channel."""

    def __init__(self) -> None:
        # channel_id -> list of WebSocket connections
        self._connections: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, channel_id: int) -> None:
        await websocket.accept()
        self._connections[channel_id].append(websocket)
        logger.info("WebSocket connected to channel %s", channel_id)

    def disconnect(self, websocket: WebSocket, channel_id: int) -> None:
        connections = self._connections.get(channel_id, [])
        if websocket in connections:
            connections.remove(websocket)
        logger.info("WebSocket disconnected from channel %s", channel_id)

    async def broadcast(self, channel_id: int, payload: dict) -> None:
        """Broadcast a JSON payload to all connections in a channel."""
        dead: List[WebSocket] = []
        for ws in list(self._connections.get(channel_id, [])):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel_id)

    async def send_personal(self, websocket: WebSocket, payload: dict) -> None:
        await websocket.send_text(json.dumps(payload))


manager = ConnectionManager()
