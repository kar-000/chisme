"""
chisme — FastAPI backend entry point.

UI palette reference (from COLOR_REFERENCE.md warm CRT theme):
  --crt-teal:       #00CED1  primary text / glow
  --crt-teal-light: #5DADE2  usernames / highlights
  --crt-pink:       #FFB6C1  own messages
  --crt-orange:     #FF8C42  unread badges / notices
  --crt-dark:       #1a1612  main background
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api import auth, channels, dms, gifs, health, messages, push, search, uploads, users
from app.api.presence import bulk_router
from app.api.presence import router as presence_router
from app.api.voice import router as voice_router
from app.config import settings
from app.database import configure_wal_for_replication, get_db
from app.redis.client import close_redis, init_redis
from app.websocket.handlers import channel_ws_handler, dm_ws_handler
from app.websocket.voice_handler import voice_ws_handler

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
configure_wal_for_replication()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield
    await close_redis()


app = FastAPI(
    title="chisme",
    description="Retro IRC-style chat — warm CRT aesthetic",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# allow_origins=["*"] is incompatible with allow_credentials=True in the CORS
# spec. When the wildcard is present (dev), switch to allow_origin_regex=".*"
# which achieves the same effect without triggering Starlette's guard.
_cors_origins = [o for o in settings.CORS_ORIGINS if o != "*"]
_cors_regex = ".*" if len(_cors_origins) < len(settings.CORS_ORIGINS) else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(channels.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(gifs.router, prefix="/api")
app.include_router(dms.router, prefix="/api")
app.include_router(presence_router, prefix="/api")
app.include_router(bulk_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(push.router, prefix="/api")

# Serve uploaded files as static assets
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws/channels/{channel_id}")
async def websocket_endpoint(websocket: WebSocket, channel_id: int, db: Session = Depends(get_db)) -> None:
    await channel_ws_handler(websocket, channel_id, db)


@app.websocket("/ws/dm/{dm_id}")
async def dm_websocket_endpoint(websocket: WebSocket, dm_id: int, db: Session = Depends(get_db)) -> None:
    await dm_ws_handler(websocket, dm_id, db)


@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)) -> None:
    await voice_ws_handler(websocket, db)


# ---------------------------------------------------------------------------
# Custom exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})
