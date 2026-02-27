"""
Voice REST API — query who is in a voice channel, and fetch ICE server config.

Endpoints:
  GET /api/channels/{channel_id}/voice   → list of users currently in voice
  GET /api/voice/ice-servers             → STUN/TURN server list for WebRTC
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.channel import Channel
from app.models.user import User
from app.redis import voice as voice_mgr

router = APIRouter(prefix="/channels", tags=["voice"])
ice_router = APIRouter(prefix="/voice", tags=["voice"])


@ice_router.get("/ice-servers")
async def get_ice_servers(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return ICE server config for WebRTC peer connections."""
    servers: list[dict] = [{"urls": "stun:stun.l.google.com:19302"}]
    if settings.TURN_SERVER and settings.TURN_USERNAME and settings.TURN_PASSWORD:
        port_suffix = "" if ":" in settings.TURN_SERVER else ":3478"
        servers.append(
            {
                "urls": f"turn:{settings.TURN_SERVER}{port_suffix}",
                "username": settings.TURN_USERNAME,
                "credential": settings.TURN_PASSWORD,
            }
        )
    return {"ice_servers": servers}


class VoiceUser(BaseModel):
    user_id: int
    muted: bool
    video: bool


class VoiceChannelResponse(BaseModel):
    channel_id: int
    users: list[VoiceUser]


@router.get("/{channel_id}/voice", response_model=VoiceChannelResponse)
async def get_voice_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VoiceChannelResponse:
    """Return the list of users currently in voice for a channel."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    user_ids = await voice_mgr.get_channel_voice_users(channel_id)
    if not user_ids:
        return VoiceChannelResponse(channel_id=channel_id, users=[])

    states = await voice_mgr.get_bulk_voice_states(user_ids)
    voice_users = [
        VoiceUser(
            user_id=uid,
            muted=state.get("muted", True) if state else True,
            video=state.get("video", False) if state else False,
        )
        for uid, state in states.items()
    ]
    return VoiceChannelResponse(channel_id=channel_id, users=voice_users)
