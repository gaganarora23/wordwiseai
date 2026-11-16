import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Text, false, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WordMastery(Base):
    """A child's progress on a word, keyed by (child, word). ``needs_review`` is separate from ``status``.

    Rows are created when a word is first answered in a completed session, so ``NEW`` rows are not pre-created.
    """

    __tablename__ = "word_mastery"
    __table_args__ = (
        CheckConstraint("status IN ('NEW', 'LEARNING', 'MASTERED')", name="status_valid"),
        CheckConstraint("consecutive_correct BETWEEN 0 AND 3", name="consecutive_correct_valid"),
        CheckConstraint(
            "(status = 'NEW' AND consecutive_correct = 0 AND last_practiced_at IS NULL AND needs_review = false)"
            " OR (status = 'LEARNING' AND consecutive_correct BETWEEN 0 AND 2 AND last_practiced_at IS NOT NULL)"
            " OR (status = 'MASTERED' AND consecutive_correct = 3 AND last_practiced_at IS NOT NULL)",
            name="status_progress",
        ),
    )

    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("children.id", ondelete="CASCADE"), primary_key=True
    )
    word_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("words.id"), primary_key=True)
    status: Mapped[str] = mapped_column(Text, server_default=text("'NEW'"))
    consecutive_correct: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    needs_review: Mapped[bool] = mapped_column(Boolean, server_default=false())
