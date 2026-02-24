"""Channel Notes API — GET/PUT notes and revision history."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.channel import Channel
from app.models.channel_notes import ChannelNotes, ChannelNotesHistory
from app.models.server_membership import ServerMembership
from app.models.user import User
from app.schemas.channel_notes import (
    ChannelNotesHistoryEntry,
    ChannelNotesResponse,
    ChannelNotesUpdate,
)
from app.websocket.manager import manager

router = APIRouter(tags=["channel_notes"])


def _notes_response(notes: ChannelNotes) -> ChannelNotesResponse:
    return ChannelNotesResponse(
        id=notes.id,
        channel_id=notes.channel_id,
        content=notes.content,
        updated_by=notes.updated_by,
        updated_by_username=notes.editor.username if notes.editor else None,
        updated_at=notes.updated_at,
        version=notes.version,
    )


def _check_membership(channel_id: int, user_id: int, db: Session) -> Channel:
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    member = db.query(ServerMembership).filter_by(server_id=channel.server_id, user_id=user_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    return channel


@router.get(
    "/api/channels/{channel_id}/notes",
    response_model=ChannelNotesResponse | None,
)
async def get_channel_notes(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChannelNotesResponse | None:
    _check_membership(channel_id, current_user.id, db)
    notes = db.query(ChannelNotes).filter_by(channel_id=channel_id).first()
    if not notes:
        return None
    return _notes_response(notes)


@router.put(
    "/api/channels/{channel_id}/notes",
    response_model=ChannelNotesResponse,
)
async def upsert_channel_notes(
    channel_id: int,
    body: ChannelNotesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChannelNotesResponse:
    channel = _check_membership(channel_id, current_user.id, db)
    notes = db.query(ChannelNotes).filter_by(channel_id=channel_id).first()

    if notes is None:
        # First save — create the record
        notes = ChannelNotes(
            channel_id=channel_id,
            content=body.content,
            updated_by=current_user.id,
            updated_at=datetime.now(timezone.utc),
            version=1,
        )
        db.add(notes)
        db.flush()
    else:
        # Optimistic lock check
        if body.base_version is not None and notes.version != body.base_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Version conflict",
                    "server_version": notes.version,
                    "server_content": notes.content,
                },
            )
        # Save history entry for the previous version
        history = ChannelNotesHistory(
            notes_id=notes.id,
            content=notes.content,
            edited_by=notes.updated_by or current_user.id,
            edited_at=notes.updated_at,
            version=notes.version,
        )
        db.add(history)

        notes.content = body.content
        notes.updated_by = current_user.id
        notes.updated_at = datetime.now(timezone.utc)
        notes.version += 1

    db.commit()
    db.refresh(notes)

    # Broadcast to all server members
    await manager.broadcast_to_server(
        channel.server_id,
        {
            "type": "channel_notes_updated",
            "channel_id": channel_id,
            "content": notes.content,
            "updated_by": current_user.username,
            "version": notes.version,
        },
    )

    return _notes_response(notes)


@router.get(
    "/api/channels/{channel_id}/notes/history",
    response_model=list[ChannelNotesHistoryEntry],
)
async def get_channel_notes_history(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChannelNotesHistoryEntry]:
    _check_membership(channel_id, current_user.id, db)
    notes = db.query(ChannelNotes).filter_by(channel_id=channel_id).first()
    if not notes:
        return []
    history = (
        db.query(ChannelNotesHistory)
        .filter_by(notes_id=notes.id)
        .order_by(ChannelNotesHistory.version.desc())
        .limit(10)
        .all()
    )
    return [
        ChannelNotesHistoryEntry(
            id=h.id,
            version=h.version,
            content=h.content,
            edited_by=h.edited_by,
            edited_by_username=h.editor.username if h.editor else None,
            edited_at=h.edited_at,
        )
        for h in history
    ]
