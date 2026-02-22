from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    # Channel names displayed with #-prefix in --crt-teal (#00CED1) sidebar.
    # Names must be unique within a server, enforced by unique_channel_per_server.
    name = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    server = relationship("Server", back_populates="channels")
    creator = relationship("User", back_populates="channels_created")
    messages = relationship("Message", back_populates="channel", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("server_id", "name", name="unique_channel_per_server"),)
