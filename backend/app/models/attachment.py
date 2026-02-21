from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    # NULL until the message is sent; set to message.id on message creation
    message_id = Column(
        Integer,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)  # UUID-based stored name
    original_filename = Column(String(255), nullable=False)  # User-visible name
    mime_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)  # bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    external_url = Column(String(2048), nullable=True)  # Tenor/CDN URL (no local file)
    thumbnail_filename = Column(String(255), nullable=True)  # thumb_{uuid}.jpg for images

    # Relationships
    message = relationship("Message", back_populates="attachments")
    uploader = relationship("User")
