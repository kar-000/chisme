import secrets

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ServerInvite(Base):
    """An invite link that grants membership to a server when redeemed."""

    __tablename__ = "server_invites"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(12), unique=True, index=True, nullable=False)
    max_uses = Column(Integer, nullable=True)  # None = unlimited
    use_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # None = never
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    server = relationship("Server", back_populates="invites")
    creator = relationship("User", foreign_keys=[created_by])

    @staticmethod
    def generate_code() -> str:
        """Generate a 12-character URL-safe random code."""
        return secrets.token_urlsafe(9)[:12]
