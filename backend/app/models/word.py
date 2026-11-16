import uuid

from sqlalchemy import CheckConstraint, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.child import GRADES_SQL


class Word(Base):
    """A vocabulary word with its four prewritten options.

    Options are four NOT NULL columns plus ``correct_option`` (1-4): PostgreSQL
    then guarantees exactly four options and exactly one correct one.
    """

    __tablename__ = "words"
    __table_args__ = (
        CheckConstraint(f"grade IN ({GRADES_SQL})", name="grade_valid"),
        CheckConstraint("correct_option BETWEEN 1 AND 4", name="correct_option_valid"),
        CheckConstraint(
            "btrim(option_1) <> '' AND btrim(option_2) <> '' "
            "AND btrim(option_3) <> '' AND btrim(option_4) <> ''",
            name="options_not_blank",
        ),
        CheckConstraint("btrim(explanation) <> ''", name="explanation_not_blank"),
    )

    # Supplied by the caller (stable IDs for ingestion), so no default.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    word: Mapped[str] = mapped_column(Text)
    grade: Mapped[str] = mapped_column(Text)
    definition: Mapped[str] = mapped_column(Text)
    example: Mapped[str] = mapped_column(Text)
    syllables: Mapped[str] = mapped_column(Text)
    content_version: Mapped[str] = mapped_column(Text)
    option_1: Mapped[str] = mapped_column(Text)
    option_2: Mapped[str] = mapped_column(Text)
    option_3: Mapped[str] = mapped_column(Text)
    option_4: Mapped[str] = mapped_column(Text)
    correct_option: Mapped[int] = mapped_column(SmallInteger)
    explanation: Mapped[str] = mapped_column(Text)
