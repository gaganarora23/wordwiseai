import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class QuizResult(Base):
    """The result of a completed session; the primary key gives at most one result per session.

    ``review_word_ids`` holds the words missed or answered correctly only after a hint. PostgreSQL cannot
    put a foreign key on array elements, so that (and distinctness) is left to the writing code (#27).
    """

    __tablename__ = "quiz_results"
    __table_args__ = (
        CheckConstraint(
            "correct_count >= 0 AND incorrect_count >= 0 AND correct_count + incorrect_count BETWEEN 1 AND 10",
            name="counts_valid",
        ),
        CheckConstraint("score = correct_count", name="score_valid"),
        CheckConstraint("array_position(review_word_ids, NULL) IS NULL", name="review_word_ids_no_nulls"),
        CheckConstraint(
            "cardinality(review_word_ids) BETWEEN incorrect_count AND correct_count + incorrect_count",
            name="review_word_ids_length",
        ),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    score: Mapped[int] = mapped_column(Integer)
    correct_count: Mapped[int] = mapped_column(Integer)
    incorrect_count: Mapped[int] = mapped_column(Integer)
    review_word_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), server_default=text("'{}'::uuid[]")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
