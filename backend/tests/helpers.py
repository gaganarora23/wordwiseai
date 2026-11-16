"""Insert helpers for tests. They take a Connection or Session, do not commit, and return the new id.

Defaults satisfy the database constraints; keyword arguments override any column.
"""

import uuid
from pathlib import Path

from sqlalchemy import text

# Development vocabulary (#12): pass it to the ingestion command or its functions. Not release content.
VOCABULARY_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "vocabulary"

CHILD = {"nickname": "Sam", "grade": "3", "daily_goal": 5}
WORD = {
    "word": "banana", "grade": "1", "definition": "a fruit", "example": "I ate a banana.",
    "syllables": "ba · na · na", "content_version": "v1",
    "option_1": "a", "option_2": "b", "option_3": "c", "option_4": "d",
    "correct_option": 1, "explanation": "Because.",
}


def _insert(connection, table, values):
    columns = ", ".join(values)
    params = ", ".join(f":{key}" for key in values)
    connection.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({params})"), values)


def insert_child(connection, **overrides):
    values = {"id": uuid.uuid4(), **CHILD, **overrides}
    _insert(connection, "children", values)
    return values["id"]


def insert_word(connection, **overrides):
    values = {"id": uuid.uuid4(), **WORD, **overrides}
    _insert(connection, "words", values)
    return values["id"]


def insert_session_with_words(connection, *, word_ids=None, word_count=2, **overrides):
    """Insert a session and its ``session_words`` (positions 0..n-1); returns the session id.

    Creates the child unless ``child_id`` is given, and the words unless ``word_ids`` is given.
    """
    values = {
        "id": uuid.uuid4(), "mode": "daily", "phase": "learning", "status": "in_progress",
        "current_position": 0, "completed_at": None, "abandoned_at": None, **overrides,
    }
    if "child_id" not in values:
        values["child_id"] = insert_child(connection)
    if word_ids is None:
        word_ids = [insert_word(connection, word=f"word{i}") for i in range(word_count)]
    _insert(connection, "sessions", values)
    for position, word_id in enumerate(word_ids):
        _insert(connection, "session_words", {"session_id": values["id"], "word_id": word_id, "position": position})
    return values["id"]
