from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class DirectMessageChannel(Base):
    """A 1-on-1 DM conversation between two users."""

    __tablename__ = "dm_channels"

    id = Column(Integer, primary_key=True, index=True)
    # Always store the lower user_id as user1_id to guarantee uniqueness
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    messages = relationship("Message", back_populates="dm_channel", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="unique_dm_pair"),
    )

    @classmethod
    def get_or_create(cls, db, a: int, b: int) -> "DirectMessageChannel":
        uid1, uid2 = (a, b) if a < b else (b, a)
        dm = db.query(cls).filter(cls.user1_id == uid1, cls.user2_id == uid2).first()
        if not dm:
            dm = cls(user1_id=uid1, user2_id=uid2)
            db.add(dm)
            db.commit()
            db.refresh(dm)
        return dm

    def other_user(self, current_user_id: int):
        return self.user2 if self.user1_id == current_user_id else self.user1
