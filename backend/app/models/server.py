from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Server(Base):
    """A named community. Users join servers and see only the channels
    and members belonging to the servers they have joined."""

    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(500), nullable=True)
    icon_url = Column(String(500), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    is_suspended = Column(Boolean, default=False, nullable=False)
    suspended_reason = Column(String(500), nullable=True)
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    memberships = relationship("ServerMembership", back_populates="server", cascade="all, delete-orphan")
    channels = relationship("Channel", back_populates="server", cascade="all, delete-orphan")
    invites = relationship("ServerInvite", back_populates="server", cascade="all, delete-orphan")
