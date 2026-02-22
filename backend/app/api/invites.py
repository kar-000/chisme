from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_server_admin
from app.database import get_db
from app.models.server_invite import ServerInvite
from app.models.server_membership import ROLE_MEMBER, ServerMembership
from app.models.user import User

router = APIRouter()


def _get_valid_invite(code: str, db: Session) -> ServerInvite:
    """Shared validation: raises 404 or 410 for missing/expired/revoked invites."""
    invite = db.query(ServerInvite).filter(ServerInvite.code == code).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if not invite.is_active:
        raise HTTPException(
            status_code=410,
            detail="This invite has been revoked",
        )
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        invite.is_active = False
        db.commit()
        raise HTTPException(status_code=410, detail="This invite has expired")
    if invite.max_uses and invite.use_count >= invite.max_uses:
        raise HTTPException(
            status_code=410,
            detail="This invite has reached its maximum number of uses",
        )
    return invite


@router.post("/api/servers/{server_id}/invites", status_code=201)
async def create_invite(
    server_id: int,
    body: dict,
    membership: ServerMembership = Depends(require_server_admin),
    db: Session = Depends(get_db),
):
    """
    Generate an invite code for this server. Admin or owner only.
    Optional body fields: max_uses (int), expires_in_hours (int).
    """
    max_uses: int | None = body.get("max_uses")
    expires_in_hours: int | None = body.get("expires_in_hours")

    expires_at = None
    if expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

    invite = ServerInvite(
        server_id=server_id,
        created_by=membership.user_id,
        code=ServerInvite.generate_code(),
        max_uses=max_uses,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return {
        "code": invite.code,
        "expires_at": invite.expires_at,
        "max_uses": invite.max_uses,
        "use_count": invite.use_count,
    }


@router.get("/api/invites/{code}")
async def preview_invite(code: str, db: Session = Depends(get_db)):
    """
    Preview an invite without redeeming it. No authentication required.
    Returns server name and member count so the user knows what they're joining.
    """
    invite = _get_valid_invite(code, db)
    return {
        "server_name": invite.server.name,
        "server_description": invite.server.description,
        "server_icon_url": invite.server.icon_url,
        "member_count": len(invite.server.memberships),
    }


@router.post("/api/invites/{code}/redeem")
async def redeem_invite(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Redeem an invite code. Adds the current user as a member of the server.
    Idempotent — redeeming an invite you've already used returns success silently.
    """
    invite = _get_valid_invite(code, db)

    # Already a member — return success without duplicating the row
    existing = (
        db.query(ServerMembership)
        .filter(
            ServerMembership.server_id == invite.server_id,
            ServerMembership.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        return {"server_id": invite.server_id, "already_member": True}

    membership = ServerMembership(
        server_id=invite.server_id,
        user_id=current_user.id,
        role=ROLE_MEMBER,
    )
    db.add(membership)

    invite.use_count += 1
    if invite.max_uses and invite.use_count >= invite.max_uses:
        invite.is_active = False

    db.commit()
    return {"server_id": invite.server_id, "already_member": False}


@router.delete(
    "/api/servers/{server_id}/invites/{code}",
    status_code=204,
)
async def revoke_invite(
    server_id: int,
    code: str,
    membership: ServerMembership = Depends(require_server_admin),
    db: Session = Depends(get_db),
):
    """Revoke an active invite. Admin or owner only."""
    invite = (
        db.query(ServerInvite)
        .filter(
            ServerInvite.code == code,
            ServerInvite.server_id == server_id,
        )
        .first()
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    invite.is_active = False
    db.commit()
