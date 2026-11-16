import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Same values the frontend and API use (frontend/src/services/types.ts).
GRADES = ("K", *(str(n) for n in range(1, 13)))
GRADES_SQL = ", ".join(f"'{g}'" for g in GRADES)


class Child(Base):
    __tablename__ = "children"
    __table_args__ = (
        CheckConstraint("char_length(nickname) BETWEEN 1 AND 20", name="nickname_length"),
        CheckConstraint(f"grade IN ({GRADES_SQL})", name="grade_valid"),
        CheckConstraint("daily_goal IN (5, 10)", name="daily_goal_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nickname: Mapped[str] = mapped_column(Text)
    grade: Mapped[str] = mapped_column(Text)
    daily_goal: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
