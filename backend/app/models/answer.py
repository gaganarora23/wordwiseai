import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, SmallInteger, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Answer(Base):
    """One answer per word per session. ``selected_option`` uses the 1-4 numbering of ``Word.correct_option``."""

    __tablename__ = "answers"
    __table_args__ = (
        CheckConstraint("selected_option BETWEEN 1 AND 4", name="selected_option_valid"),
        # The answered word must belong to the session.
        ForeignKeyConstraint(
            ["session_id", "word_id"],
            ["session_words.session_id", "session_words.word_id"],
            name="fk_answers_session_id_word_id_session_words",
        ),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    word_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("words.id"), primary_key=True)
    selected_option: Mapped[int] = mapped_column(SmallInteger)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    hint_used: Mapped[bool] = mapped_column(Boolean)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
