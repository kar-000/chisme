from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Multi-server identity — always set to settings.SERVER_DOMAIN for local users.
    # Future federated users from other servers will have a different home_server.
    home_server = Column(String(255), nullable=False, index=True, server_default="local")

    avatar_url = Column(String(500), nullable=True)
    display_name = Column(String(50), nullable=True)
    bio = Column(String(500), nullable=True)
    # CRT teal palette: status displayed with --crt-teal (#00CED1) in the UI
    status = Column(String(100), default="online")
    is_active = Column(Boolean, default=True)
    # Site-level flags — set directly in the database, never via API.
    # is_site_admin: full operator access to /api/operator/ endpoints.
    # can_create_server: allows creating new servers (disabled by default on
    # closed-registration deployments).
    is_site_admin = Column(Boolean, default=False, nullable=False)
    can_create_server = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    messages = relationship("Message", back_populates="user")
    channels_created = relationship("Channel", back_populates="creator")
    reactions = relationship("Reaction", back_populates="user")
    server_memberships = relationship("ServerMembership", back_populates="user")
    push_subscriptions = relationship(
        "PushSubscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def qualified_name(self) -> str:
        """Returns username@home_server — the globally unique identity."""
        return f"{self.username}@{self.home_server}"
