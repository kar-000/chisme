from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ChannelNotes(Base):
    __tablename__ = "channel_notes"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    content = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    version = Column(Integer, default=1, nullable=False)

    channel = relationship("Channel")
    editor = relationship("User")
    history = relationship(
        "ChannelNotesHistory",
        back_populates="notes",
        order_by="ChannelNotesHistory.version.desc()",
    )


class ChannelNotesHistory(Base):
    __tablename__ = "channel_notes_history"

    id = Column(Integer, primary_key=True, index=True)
    notes_id = Column(
        Integer,
        ForeignKey("channel_notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(Text, nullable=True)
    edited_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    edited_at = Column(DateTime(timezone=True), server_default=func.now())
    version = Column(Integer, nullable=False)

    notes = relationship("ChannelNotes", back_populates="history")
    editor = relationship("User")
