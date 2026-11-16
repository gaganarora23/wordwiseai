import uuid

from pydantic import BaseModel


class AnswerOption(BaseModel):
    id: str
    text: str
    is_correct: bool


class WordOut(BaseModel):
    id: uuid.UUID
    word: str
    grade: str
    definition: str
    example: str
    syllables: str
    content_version: str
    options: list[AnswerOption]
    explanation: str
