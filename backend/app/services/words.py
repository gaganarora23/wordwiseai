from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.word import Word
from app.schemas.word import AnswerOption, WordOut


def list_words_for_grade(session: Session, grade: str) -> list[WordOut]:
    """Words of one grade in stable order (id ascending); an empty list if the grade has none."""
    rows = session.scalars(select(Word).where(Word.grade == grade).order_by(Word.id)).all()
    return [_to_schema(row) for row in rows]


def _to_schema(row: Word) -> WordOut:
    texts = [row.option_1, row.option_2, row.option_3, row.option_4]
    return WordOut(
        id=row.id,
        word=row.word,
        grade=row.grade,
        definition=row.definition,
        example=row.example,
        syllables=row.syllables,
        content_version=row.content_version,
        options=[
            AnswerOption(id=str(n), text=text, is_correct=n == row.correct_option)
            for n, text in enumerate(texts, start=1)
        ],
        explanation=row.explanation,
    )
