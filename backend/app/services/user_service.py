from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.server_membership import ServerMembership
    from app.models.user import User


def get_display_name(user: User, membership: ServerMembership | None = None) -> str:
    """Resolve the effective display name for a user in a server context.

    Priority: nickname (per-server) → display_name (global) → username
    """
    if membership and membership.nickname:
        return membership.nickname
    if user.display_name:
        return user.display_name
    return user.username


def get_membership(db: Session, user_id: int, server_id: int) -> ServerMembership | None:
    """Return the ServerMembership for the given user+server, or None."""
    from app.models.server_membership import ServerMembership

    return db.query(ServerMembership).filter_by(user_id=user_id, server_id=server_id).first()
