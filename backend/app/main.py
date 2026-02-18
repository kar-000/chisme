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

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api import auth, channels, health, messages, uploads, users
from app.config import settings
from app.database import get_db
from app.websocket.handlers import channel_ws_handler

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="chisme",
    description="Retro IRC-style chat — warm CRT aesthetic",
    version="1.0.0",
    debug=settings.DEBUG,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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

# Serve uploaded files as static assets
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/channels/{channel_id}")
async def websocket_endpoint(websocket: WebSocket, channel_id: int) -> None:
    db: Session = next(get_db())
    try:
        await channel_ws_handler(websocket, channel_id, db)
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Custom exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})
