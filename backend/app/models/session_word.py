import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SessionWord(Base):
    """A word in a session, at a zero-based display position. The primary key is UNIQUE(session_id, word_id)."""

    __tablename__ = "session_words"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_valid"),
        UniqueConstraint("session_id", "position", name="uq_session_words_session_id_position"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    word_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("words.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
