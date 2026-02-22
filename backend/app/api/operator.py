"""
Operator endpoints — accessible only to users with is_site_admin = True.

These are never linked from the regular UI. A user who discovers these routes
gets a 403 unless they have the site admin flag set directly in the database.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_site_admin
from app.database import get_db
from app.models.server import Server
from app.models.server_membership import ROLE_OWNER, ServerMembership
from app.models.user import User

router = APIRouter(prefix="/api/operator")


# ── Server Management ─────────────────────────────────────────────────────────


@router.get("/servers")
async def list_all_servers(
    admin: User = Depends(require_site_admin),
    db: Session = Depends(get_db),
):
    """List every server on the deployment regardless of membership."""
    servers = db.query(Server).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "slug": s.slug,
            "owner_id": s.owner_id,
            "member_count": len(s.memberships),
            "is_suspended": s.is_suspended,
            "suspended_reason": s.suspended_reason,
            "created_at": s.created_at,
        }
        for s in servers
    ]


@router.post("/servers/{server_id}/suspend")
async def suspend_server(
    server_id: int,
    body: dict,
    admin: User = Depends(require_site_admin),
    db: Session = Depends(get_db),
):
    """
    Suspend a server. All members (including the owner) lose access.
    Data is retained — suspension is reversible via /unsuspend.
    Requires a 'reason' field in the request body.
    """
    reason: str = body.get("reason", "")
    if not reason:
        raise HTTPException(status_code=422, detail="A suspension reason is required")

    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    server.is_suspended = True
    server.suspended_reason = reason
    server.suspended_at = datetime.utcnow()
    db.commit()
    return {"status": "suspended", "server_id": server_id}


@router.post("/servers/{server_id}/unsuspend")
async def unsuspend_server(
    server_id: int,
    admin: User = Depends(require_site_admin),
    db: Session = Depends(get_db),
):
    """Lift a suspension. The server becomes accessible again immediately."""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    server.is_suspended = False
    server.suspended_reason = None
    server.suspended_at = None
    db.commit()
    return {"status": "active", "server_id": server_id}


@router.delete("/servers/{server_id}", status_code=204)
async def operator_delete_server(
    server_id: int,
    admin: User = Depends(require_site_admin),
    db: Session = Depends(get_db),
):
    """
    Permanently delete a server and all its contents.
    This is irreversible. Prefer /suspend for temporary action.
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    db.delete(server)
    db.commit()


@router.post("/servers/{server_id}/reassign-owner")
async def operator_reassign_owner(
    server_id: int,
    body: dict,
    admin: User = Depends(require_site_admin),
    db: Session = Depends(get_db),
):
    """
    Force-reassign server ownership to any user on the deployment.
    Used when the original owner account is unavailable.
    The new owner is added as a member if not already one.
    The previous owner's membership (if it still exists) is demoted to admin.
    """
    new_owner_id: int = body.get("new_owner_id")
    if not new_owner_id:
        raise HTTPException(status_code=422, detail="new_owner_id is required")

    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    new_owner = db.query(User).filter(User.id == new_owner_id).first()
    if not new_owner:
        raise HTTPException(status_code=404, detail="User not found")

    # Demote the previous owner if their membership record still exists
    old_membership = (
        db.query(ServerMembership)
        .filter(
            ServerMembership.server_id == server_id,
            ServerMembership.user_id == server.owner_id,
        )
        .first()
    )
    if old_membership:
        old_membership.role = "admin"

    # Add or promote the new owner
    new_membership = (
        db.query(ServerMembership)
        .filter(
            ServerMembership.server_id == server_id,
            ServerMembership.user_id == new_owner_id,
        )
        .first()
    )
    if new_membership:
        new_membership.role = ROLE_OWNER
    else:
        new_membership = ServerMembership(
            server_id=server_id,
            user_id=new_owner_id,
            role=ROLE_OWNER,
        )
        db.add(new_membership)

    previous_owner_id = server.owner_id
    server.owner_id = new_owner_id
    db.commit()

    return {
        "status": "reassigned",
        "server_id": server_id,
        "new_owner_id": new_owner_id,
        "previous_owner_id": previous_owner_id,
    }


# ── User Management ───────────────────────────────────────────────────────────


@router.get("/users")
async def list_all_users(
    admin: User = Depends(require_site_admin),
    db: Session = Depends(get_db),
):
    """List all registered users on the deployment."""
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_active": u.is_active,
            "is_site_admin": u.is_site_admin,
            "can_create_server": u.can_create_server,
            "server_count": len(u.server_memberships),
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: int,
    admin: User = Depends(require_site_admin),
    db: Session = Depends(get_db),
):
    """
    Disable a user account. The user cannot log in and appears offline
    across all servers. Data is retained. Reversible via /enable.
    Cannot disable another site admin or yourself.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_site_admin:
        raise HTTPException(status_code=403, detail="Cannot disable a site admin")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")

    user.is_active = False
    db.commit()
    return {"status": "disabled", "user_id": user_id}


@router.post("/users/{user_id}/enable")
async def enable_user(
    user_id: int,
    admin: User = Depends(require_site_admin),
    db: Session = Depends(get_db),
):
    """Re-enable a disabled user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()
    return {"status": "active", "user_id": user_id}
