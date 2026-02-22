from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    require_can_create_server,
    require_server_admin,
    require_server_member,
    require_server_owner,
)
from app.database import get_db
from app.models.server import Server
from app.models.server_membership import (
    ROLE_ADMIN,
    ROLE_MEMBER,
    ROLE_OWNER,
    ServerMembership,
)
from app.models.user import User
from app.schemas.server import ServerCreate, ServerMembershipResponse, ServerResponse, ServerUpdate
from app.services.notifications import notify_server_created

router = APIRouter()


@router.get("/api/servers", response_model=list[ServerResponse])
async def list_my_servers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all servers the current user belongs to."""
    memberships = db.query(ServerMembership).filter(ServerMembership.user_id == current_user.id).all()
    server_ids = [m.server_id for m in memberships]
    role_by_server = {m.server_id: m.role for m in memberships}

    servers = db.query(Server).filter(Server.id.in_(server_ids)).all()

    result = []
    for server in servers:
        data = ServerResponse.model_validate(server)
        data.member_count = len(server.memberships)
        data.current_user_role = role_by_server.get(server.id)
        result.append(data)
    return result


@router.post("/api/servers", response_model=ServerResponse, status_code=201)
async def create_server(
    data: ServerCreate,
    current_user: User = Depends(require_can_create_server),
    db: Session = Depends(get_db),
):
    """Create a new server. Creator becomes owner and first member."""
    existing = db.query(Server).filter(Server.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="A server with this slug already exists")

    server = Server(
        name=data.name,
        slug=data.slug,
        description=data.description,
        owner_id=current_user.id,
        is_public=data.is_public,
    )
    db.add(server)
    db.flush()  # get server.id before adding membership

    membership = ServerMembership(
        server_id=server.id,
        user_id=current_user.id,
        role=ROLE_OWNER,
    )
    db.add(membership)
    db.commit()
    db.refresh(server)

    notify_server_created(
        server_name=server.name,
        server_slug=server.slug,
        owner_username=current_user.username,
    )

    response = ServerResponse.model_validate(server)
    response.member_count = 1
    response.current_user_role = ROLE_OWNER
    return response


@router.get("/api/servers/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: int,
    membership: ServerMembership = Depends(require_server_member),
    db: Session = Depends(get_db),
):
    """Get server details. Membership required."""
    server = db.query(Server).filter(Server.id == server_id).first()
    response = ServerResponse.model_validate(server)
    response.member_count = len(server.memberships)
    response.current_user_role = membership.role
    return response


@router.patch("/api/servers/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: int,
    data: ServerUpdate,
    membership: ServerMembership = Depends(require_server_admin),
    db: Session = Depends(get_db),
):
    """Update server name, description, or icon. Admin or owner only."""
    server = db.query(Server).filter(Server.id == server_id).first()

    if data.name is not None:
        server.name = data.name
    if data.description is not None:
        server.description = data.description
    if data.icon_url is not None:
        server.icon_url = data.icon_url
    if data.is_public is not None:
        server.is_public = data.is_public

    db.commit()
    db.refresh(server)

    response = ServerResponse.model_validate(server)
    response.member_count = len(server.memberships)
    response.current_user_role = membership.role
    return response


@router.delete("/api/servers/{server_id}", status_code=204)
async def delete_server(
    server_id: int,
    membership: ServerMembership = Depends(require_server_owner),
    db: Session = Depends(get_db),
):
    """Delete server and all contents. Owner only."""
    server = db.query(Server).filter(Server.id == server_id).first()
    db.delete(server)
    db.commit()


@router.get(
    "/api/servers/{server_id}/members",
    response_model=list[ServerMembershipResponse],
)
async def list_members(
    server_id: int,
    membership: ServerMembership = Depends(require_server_member),
    db: Session = Depends(get_db),
):
    """List all members of this server. Membership required."""
    memberships = db.query(ServerMembership).filter(ServerMembership.server_id == server_id).all()
    return [
        ServerMembershipResponse(
            user_id=m.user_id,
            username=m.user.username,
            avatar_url=m.user.avatar_url,
            display_name=m.user.display_name,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in memberships
    ]


@router.delete("/api/servers/{server_id}/members/{target_user_id}", status_code=204)
async def remove_member(
    server_id: int,
    target_user_id: int,
    membership: ServerMembership = Depends(require_server_admin),
    db: Session = Depends(get_db),
):
    """Remove a member. Admin or owner only. Cannot remove the owner."""
    target = (
        db.query(ServerMembership)
        .filter(
            ServerMembership.server_id == server_id,
            ServerMembership.user_id == target_user_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.role == ROLE_OWNER:
        raise HTTPException(status_code=403, detail="The server owner cannot be removed")
    # Admins cannot remove other admins — only the owner can
    if target.role == ROLE_ADMIN and membership.role != ROLE_OWNER:
        raise HTTPException(status_code=403, detail="Only the owner can remove an admin")
    db.delete(target)
    db.commit()


class RoleUpdate(ServerUpdate):
    role: str


@router.patch("/api/servers/{server_id}/members/{target_user_id}/role")
async def update_member_role(
    server_id: int,
    target_user_id: int,
    body: dict,
    membership: ServerMembership = Depends(require_server_owner),
    db: Session = Depends(get_db),
):
    """Promote or demote a member. Owner only. Cannot change the owner's own role here."""

    new_role = body.get("role")
    if new_role not in (ROLE_ADMIN, ROLE_MEMBER):
        raise HTTPException(
            status_code=422,
            detail="Role must be one of: admin, member",
        )

    target = (
        db.query(ServerMembership)
        .filter(
            ServerMembership.server_id == server_id,
            ServerMembership.user_id == target_user_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.role == ROLE_OWNER:
        raise HTTPException(
            status_code=403,
            detail="Use /transfer-ownership to change the owner's role",
        )

    target.role = new_role
    db.commit()
    return {"user_id": target_user_id, "role": new_role}


@router.post("/api/servers/{server_id}/transfer-ownership")
async def transfer_ownership(
    server_id: int,
    body: dict,
    membership: ServerMembership = Depends(require_server_owner),
    db: Session = Depends(get_db),
):
    """
    Transfer server ownership to another existing member.
    The current owner is demoted to admin. Immediate and irreversible
    without a subsequent transfer.
    """
    new_owner_id = body.get("new_owner_id")
    if not new_owner_id:
        raise HTTPException(status_code=422, detail="new_owner_id is required")

    if new_owner_id == membership.user_id:
        raise HTTPException(status_code=400, detail="You are already the owner")

    new_owner_membership = (
        db.query(ServerMembership)
        .filter(
            ServerMembership.server_id == server_id,
            ServerMembership.user_id == new_owner_id,
        )
        .first()
    )
    if not new_owner_membership:
        raise HTTPException(
            status_code=400,
            detail="New owner must be an existing member of this server",
        )

    server = db.query(Server).filter(Server.id == server_id).first()
    server.owner_id = new_owner_id
    membership.role = ROLE_ADMIN
    new_owner_membership.role = ROLE_OWNER

    db.commit()
    return {
        "status": "transferred",
        "new_owner_id": new_owner_id,
        "previous_owner_id": membership.user_id,
    }
