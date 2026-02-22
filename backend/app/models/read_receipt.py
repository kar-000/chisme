from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ReadReceipt(Base):
    """Tracks the last-read message per (user, channel) pair.

    When ``last_read_message_id`` is NULL the user has never opened the channel
    and all messages are considered unread.
    """

    __tablename__ = "read_receipts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    # The highest message_id the user has seen. NULL means never read.
    last_read_message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    read_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    channel = relationship("Channel")

    __table_args__ = (UniqueConstraint("user_id", "channel_id", name="uq_read_receipt_user_channel"),)
