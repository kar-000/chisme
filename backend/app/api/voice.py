"""
Voice REST API — query who is in a voice channel.

Endpoints:
  GET /api/channels/{channel_id}/voice   → list of users currently in voice
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.channel import Channel
from app.models.user import User
from app.redis import voice as voice_mgr

router = APIRouter(prefix="/channels", tags=["voice"])


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
