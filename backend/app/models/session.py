import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Session(Base):
    """A learning session. At most one ``in_progress`` session per child (partial unique index)."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("mode IN ('daily', 'review')", name="mode_valid"),
        CheckConstraint("phase IN ('learning', 'quiz')", name="phase_valid"),
        CheckConstraint("status IN ('in_progress', 'completed', 'abandoned')", name="status_valid"),
        CheckConstraint("current_position >= 0", name="current_position_valid"),
        CheckConstraint(
            "(status = 'in_progress' AND completed_at IS NULL AND abandoned_at IS NULL)"
            " OR (status = 'completed' AND completed_at IS NOT NULL AND abandoned_at IS NULL)"
            " OR (status = 'abandoned' AND abandoned_at IS NOT NULL AND completed_at IS NULL)",
            name="status_timestamps",
        ),
        Index(
            "uq_sessions_child_id_in_progress",
            "child_id",
            unique=True,
            postgresql_where="status = 'in_progress'",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(Text)
    phase: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    current_position: Mapped[int] = mapped_column(Integer)  # zero-based
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
