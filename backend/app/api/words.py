from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.word import WordOut
from app.services import words as words_service

router = APIRouter()

Grade = Literal["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]


@router.get("/grades/{grade}/words", response_model=list[WordOut])
def get_grade_words(
    grade: Annotated[Grade, Path(description="K or 1 to 12")],
    session: Annotated[Session, Depends(get_session)],
) -> list[WordOut]:
    return words_service.list_words_for_grade(session, grade)
