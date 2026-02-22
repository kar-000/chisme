"""
Presence REST endpoints.

GET  /api/users/{user_id}/presence  — query one user's status
GET  /api/users/me/presence         — query own status
POST /api/users/me/status           — set own status (online / away / dnd)
GET  /api/presence/bulk             — query multiple users' statuses (query param: ids=1,2,3)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.redis import presence

router = APIRouter(prefix="/users", tags=["presence"])

VALID_STATUSES = {"online", "away", "dnd"}


class StatusBody(BaseModel):
    status: str


class PresenceResponse(BaseModel):
    user_id: int
    status: str


@router.get("/me/presence", response_model=PresenceResponse)
async def get_my_presence(
    current_user: User = Depends(get_current_user),
):
    s = await presence.get_status(current_user.id)
    return PresenceResponse(user_id=current_user.id, status=s)


@router.post("/me/status", response_model=PresenceResponse)
async def set_my_status(
    body: StatusBody,
    current_user: User = Depends(get_current_user),
):
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of {sorted(VALID_STATUSES)}",
        )
    await presence.set_online(current_user.id, body.status)
    return PresenceResponse(user_id=current_user.id, status=body.status)


@router.get("/{user_id}/presence", response_model=PresenceResponse)
async def get_user_presence(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    s = await presence.get_status(user_id)
    return PresenceResponse(user_id=user_id, status=s)


# Bulk endpoint lives under a separate prefix; we mount it on main.py directly.
bulk_router = APIRouter(prefix="/presence", tags=["presence"])


class BulkPresenceResponse(BaseModel):
    statuses: dict[int, str]


@bulk_router.get("/bulk", response_model=BulkPresenceResponse)
async def get_bulk_presence(
    ids: str = Query(..., description="Comma-separated user IDs, e.g. 1,2,3"),
    current_user: User = Depends(get_current_user),
):
    try:
        user_ids: list[int] = [int(i.strip()) for i in ids.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="ids must be comma-separated integers") from None
    if len(user_ids) > 200:
        raise HTTPException(status_code=400, detail="Too many ids (max 200)")
    statuses = await presence.get_bulk_status(user_ids)
    return BulkPresenceResponse(statuses=statuses)
