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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    messages = relationship("Message", back_populates="user")
    channels_created = relationship("Channel", back_populates="creator")
    reactions = relationship("Reaction", back_populates="user")

    @property
    def qualified_name(self) -> str:
        """Returns username@home_server — the globally unique identity."""
        return f"{self.username}@{self.home_server}"
