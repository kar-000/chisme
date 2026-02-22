from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.server import Server
from app.models.server_membership import ServerMembership
from app.models.user import User
from app.services import auth_service

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    user = auth_service.get_user_from_token(credentials.credentials, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return user


def require_server_member(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServerMembership:
    """
    Verifies the current user is a member of server_id.
    Returns the membership record (which carries the user's role).
    Raises 404 if the server doesn't exist, 403 if the user is not a member
    or if the server is suspended (unless the user is a site admin).
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if server.is_suspended and not current_user.is_site_admin:
        raise HTTPException(
            status_code=403,
            detail="This server has been suspended by the operator.",
        )

    membership = (
        db.query(ServerMembership)
        .filter(
            ServerMembership.server_id == server_id,
            ServerMembership.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this server")

    return membership


def require_server_admin(
    membership: ServerMembership = Depends(require_server_member),
) -> ServerMembership:
    """Requires admin or owner role within the server."""
    if membership.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return membership


def require_server_owner(
    membership: ServerMembership = Depends(require_server_member),
) -> ServerMembership:
    """Requires owner role within the server."""
    if membership.role != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return membership


def require_site_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verifies the current user is a site-level admin (is_site_admin = True).
    Used exclusively on /api/operator/ endpoints.
    Returns 403 for any non-admin, including server owners.
    """
    if not current_user.is_site_admin:
        raise HTTPException(status_code=403, detail="Operator access required")
    return current_user


def require_can_create_server(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verifies the current user may create new servers.
    Site admins implicitly pass — they can always create servers.
    Other users need can_create_server = True set by the operator.
    """
    if not (current_user.is_site_admin or current_user.can_create_server):
        raise HTTPException(
            status_code=403,
            detail=("You do not have permission to create servers. Contact the site operator."),
        )
    return current_user
