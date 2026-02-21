from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    # Message text: normal messages in --crt-teal (#00CED1), own messages in --crt-pink (#FFB6C1)
    content = Column(String(2000), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    dm_channel_id = Column(Integer, ForeignKey("dm_channels.id", ondelete="CASCADE"), nullable=True)
    reply_to_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    edited_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="messages")
    channel = relationship("Channel", back_populates="messages")
    dm_channel = relationship("DirectMessageChannel", back_populates="messages", foreign_keys=[dm_channel_id])
    reactions = relationship("Reaction", back_populates="message", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="message", cascade="all, delete-orphan")
    reply_to = relationship("Message", remote_side="Message.id", foreign_keys="Message.reply_to_id")
