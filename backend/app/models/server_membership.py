from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# Valid role values
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
VALID_ROLES = (ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER)


class ServerMembership(Base):
    """Join table between User and Server, with role information."""

    __tablename__ = "server_memberships"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # role: "owner" | "admin" | "member"
    role = Column(String(20), nullable=False, default=ROLE_MEMBER)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    server = relationship("Server", back_populates="memberships")
    user = relationship("User", back_populates="server_memberships")

    __table_args__ = (UniqueConstraint("server_id", "user_id", name="unique_server_member"),)
