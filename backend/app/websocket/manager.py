import json
import logging
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per channel and DM channel."""

    def __init__(self) -> None:
        # channel_id -> list of WebSocket connections
        self._connections: Dict[int, List[WebSocket]] = defaultdict(list)
        # dm_channel_id -> list of WebSocket connections
        self._dm_connections: Dict[int, List[WebSocket]] = defaultdict(list)

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

    async def connect_dm(self, websocket: WebSocket, dm_id: int) -> None:
        await websocket.accept()
        self._dm_connections[dm_id].append(websocket)
        logger.info("WebSocket connected to DM channel %s", dm_id)

    def disconnect_dm(self, websocket: WebSocket, dm_id: int) -> None:
        connections = self._dm_connections.get(dm_id, [])
        if websocket in connections:
            connections.remove(websocket)
        logger.info("WebSocket disconnected from DM channel %s", dm_id)

    async def broadcast_dm(self, dm_id: int, payload: dict) -> None:
        """Broadcast a JSON payload to all connections in a DM channel."""
        dead: List[WebSocket] = []
        for ws in list(self._dm_connections.get(dm_id, [])):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_dm(ws, dm_id)

    async def send_personal(self, websocket: WebSocket, payload: dict) -> None:
        await websocket.send_text(json.dumps(payload))


manager = ConnectionManager()
