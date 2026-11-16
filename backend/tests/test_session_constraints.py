"""Database constraints of ``sessions``, ``session_words`` and ``answers``, checked with raw SQL on a migrated database."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_constraints import accepted, insert_child, insert_word, rejected

NOW = "2026-01-01T00:00:00+00:00"


def insert_session(connection, **overrides):
    """Insert a session; creates the child unless ``child_id`` is given. Returns the session id."""
    values = {
        "id": uuid.uuid4(), "mode": "daily", "phase": "learning", "status": "in_progress",
        "current_position": 0, "completed_at": None, "abandoned_at": None, **overrides,
    }
    if "child_id" not in values:
        values["child_id"] = uuid.uuid4()
        insert_child(connection, id=values["child_id"])
    connection.execute(
        text(
            "INSERT INTO sessions (id, child_id, mode, phase, status, current_position, completed_at, abandoned_at) "
            "VALUES (:id, :child_id, :mode, :phase, :status, :current_position, :completed_at, :abandoned_at)"
        ),
        values,
    )
    return values["id"]


def new_word(connection):
    word_id = uuid.uuid4()
    insert_word(connection, id=word_id)
    return word_id


def insert_session_word(connection, **overrides):
    values = {"position": 0, **overrides}
    connection.execute(
        text("INSERT INTO session_words (session_id, word_id, position) VALUES (:session_id, :word_id, :position)"),
        values,
    )


def insert_answer(connection, **overrides):
    values = {"selected_option": 1, "is_correct": True, "hint_used": False, **overrides}
    columns = ", ".join(values)
    params = ", ".join(f":{k}" for k in values)
    connection.execute(text(f"INSERT INTO answers ({columns}) VALUES ({params})"), values)


def count(connection, table, where="true", **params):
    return connection.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"), params).scalar_one()


@pytest.fixture
def session_with_word(migrated_connection):
    """(session_id, word_id) with the word already in the session at position 0."""
    session_id = insert_session(migrated_connection)
    word_id = new_word(migrated_connection)
    insert_session_word(migrated_connection, session_id=session_id, word_id=word_id)
    return session_id, word_id


# --- sessions: defaults ---

def test_valid_session_inserts_and_timestamps_default_to_now(migrated_connection):
    session_id = insert_session(migrated_connection)
    row = migrated_connection.execute(
        text("SELECT created_at, updated_at, completed_at, abandoned_at FROM sessions WHERE id = :id"), {"id": session_id}
    ).one()
    assert row.created_at is not None and row.updated_at is not None
    assert row.completed_at is None and row.abandoned_at is None


# --- sessions: one in_progress per child ---

def test_second_in_progress_session_for_same_child_is_rejected(migrated_connection):
    first = insert_session(migrated_connection)
    child_id = migrated_connection.execute(text("SELECT child_id FROM sessions WHERE id = :id"), {"id": first}).scalar_one()
    rejected(insert_session, migrated_connection, child_id=child_id)


def test_second_child_can_have_its_own_in_progress_session(migrated_connection):
    insert_session(migrated_connection)
    accepted(insert_session, migrated_connection)


@pytest.mark.parametrize("status,column", [("completed", "completed_at"), ("abandoned", "abandoned_at")])
def test_child_can_have_many_finished_sessions(migrated_connection, status, column):
    child_id = uuid.uuid4()
    insert_child(migrated_connection, id=child_id)
    for _ in range(3):
        accepted(insert_session, migrated_connection, child_id=child_id, status=status, **{column: NOW})
    assert count(migrated_connection, "sessions", "child_id = :c", c=child_id) == 3


@pytest.mark.parametrize("status,column", [("completed", "completed_at"), ("abandoned", "abandoned_at")])
def test_new_in_progress_session_is_accepted_after_the_first_is_finished(migrated_connection, status, column):
    first = insert_session(migrated_connection)
    child_id = migrated_connection.execute(text("SELECT child_id FROM sessions WHERE id = :id"), {"id": first}).scalar_one()
    migrated_connection.execute(
        text(f"UPDATE sessions SET status = :s, {column} = :t WHERE id = :id"), {"s": status, "t": NOW, "id": first}
    )
    accepted(insert_session, migrated_connection, child_id=child_id)


# --- sessions: enumerations (exact match) ---

BAD_TEXT = [None, "", " daily", "daily ", "Daily", "DAILY", "done"]


@pytest.mark.parametrize("value", [*BAD_TEXT, "quiz", "learning"])
def test_session_mode_outside_allowed_values_is_rejected(migrated_connection, value):
    rejected(insert_session, migrated_connection, mode=value)


@pytest.mark.parametrize("value", ["daily", "review"])
def test_session_mode_in_allowed_values_is_accepted(migrated_connection, value):
    accepted(insert_session, migrated_connection, mode=value)


@pytest.mark.parametrize("value", [None, "", " learning", "learning ", "Learning", "LEARNING", "Quiz", "done", "daily"])
def test_session_phase_outside_allowed_values_is_rejected(migrated_connection, value):
    rejected(insert_session, migrated_connection, phase=value)


@pytest.mark.parametrize("value", ["learning", "quiz"])
def test_session_phase_in_allowed_values_is_accepted(migrated_connection, value):
    accepted(insert_session, migrated_connection, phase=value)


@pytest.mark.parametrize("value", [None, "", " in_progress", "in_progress ", "In_Progress", "IN_PROGRESS", "done", "daily"])
def test_session_status_outside_allowed_values_is_rejected(migrated_connection, value):
    rejected(insert_session, migrated_connection, status=value)


# --- sessions: current_position ---

def test_session_current_position_minus_one_is_rejected(migrated_connection):
    rejected(insert_session, migrated_connection, current_position=-1)


def test_session_current_position_null_is_rejected(migrated_connection):
    rejected(insert_session, migrated_connection, current_position=None)


@pytest.mark.parametrize("value", [0, 10])
def test_session_current_position_zero_or_positive_is_accepted(migrated_connection, value):
    accepted(insert_session, migrated_connection, current_position=value)


# --- sessions: status and timestamps agree ---

VALID_COMBINATIONS = [
    ("in_progress", None, None),
    ("completed", NOW, None),
    ("abandoned", None, NOW),
]
INVALID_COMBINATIONS = [
    ("in_progress", NOW, None),
    ("in_progress", None, NOW),
    ("in_progress", NOW, NOW),
    ("completed", None, None),
    ("completed", None, NOW),
    ("completed", NOW, NOW),
    ("abandoned", None, None),
    ("abandoned", NOW, None),
    ("abandoned", NOW, NOW),
]


@pytest.mark.parametrize("status,completed_at,abandoned_at", VALID_COMBINATIONS)
def test_status_with_matching_timestamps_is_accepted(migrated_connection, status, completed_at, abandoned_at):
    accepted(insert_session, migrated_connection, status=status, completed_at=completed_at, abandoned_at=abandoned_at)


@pytest.mark.parametrize("status,completed_at,abandoned_at", INVALID_COMBINATIONS)
def test_status_with_mismatched_timestamps_is_rejected(migrated_connection, status, completed_at, abandoned_at):
    rejected(insert_session, migrated_connection, status=status, completed_at=completed_at, abandoned_at=abandoned_at)


def test_updating_to_completed_without_completed_at_is_rejected(migrated_connection):
    session_id = insert_session(migrated_connection)
    with pytest.raises(IntegrityError):
        with migrated_connection.begin_nested():
            migrated_connection.execute(text("UPDATE sessions SET status = 'completed' WHERE id = :id"), {"id": session_id})


# --- sessions: foreign key ---

def test_session_for_missing_child_is_rejected(migrated_connection):
    rejected(insert_session, migrated_connection, child_id=uuid.uuid4())


# --- session_words ---

def test_session_word_position_minus_one_is_rejected(migrated_connection):
    rejected(insert_session_word, migrated_connection, session_id=insert_session(migrated_connection),
             word_id=new_word(migrated_connection), position=-1)


def test_session_word_position_zero_is_accepted(migrated_connection):
    accepted(insert_session_word, migrated_connection, session_id=insert_session(migrated_connection),
             word_id=new_word(migrated_connection), position=0)


def test_session_word_position_null_is_rejected(migrated_connection):
    rejected(insert_session_word, migrated_connection, session_id=insert_session(migrated_connection),
             word_id=new_word(migrated_connection), position=None)


def test_two_words_at_the_same_position_in_one_session_are_rejected(migrated_connection, session_with_word):
    session_id, _ = session_with_word
    rejected(insert_session_word, migrated_connection, session_id=session_id, word_id=new_word(migrated_connection), position=0)


def test_same_position_in_different_sessions_is_accepted(migrated_connection, session_with_word):
    accepted(insert_session_word, migrated_connection, session_id=insert_session(migrated_connection),
             word_id=new_word(migrated_connection), position=0)


def test_different_positions_in_one_session_are_accepted(migrated_connection, session_with_word):
    session_id, _ = session_with_word
    accepted(insert_session_word, migrated_connection, session_id=session_id, word_id=new_word(migrated_connection), position=1)


def test_duplicate_session_word_is_rejected(migrated_connection, session_with_word):
    session_id, word_id = session_with_word
    rejected(insert_session_word, migrated_connection, session_id=session_id, word_id=word_id, position=1)


def test_same_word_in_two_sessions_is_accepted(migrated_connection, session_with_word):
    _, word_id = session_with_word
    accepted(insert_session_word, migrated_connection, session_id=insert_session(migrated_connection), word_id=word_id)


def test_session_word_for_missing_session_is_rejected(migrated_connection):
    rejected(insert_session_word, migrated_connection, session_id=uuid.uuid4(), word_id=new_word(migrated_connection))


def test_session_word_for_missing_word_is_rejected(migrated_connection):
    rejected(insert_session_word, migrated_connection, session_id=insert_session(migrated_connection), word_id=uuid.uuid4())


# --- answers ---

def test_valid_answer_inserts_and_answered_at_defaults_to_now(migrated_connection, session_with_word):
    session_id, word_id = session_with_word
    insert_answer(migrated_connection, session_id=session_id, word_id=word_id)
    assert migrated_connection.execute(text("SELECT answered_at FROM answers")).scalar_one() is not None


@pytest.mark.parametrize("value", [0, 5, -1, None])
def test_answer_selected_option_outside_1_to_4_is_rejected(migrated_connection, session_with_word, value):
    session_id, word_id = session_with_word
    rejected(insert_answer, migrated_connection, session_id=session_id, word_id=word_id, selected_option=value)


@pytest.mark.parametrize("value", [1, 4])
def test_answer_selected_option_1_or_4_is_accepted(migrated_connection, session_with_word, value):
    session_id, word_id = session_with_word
    accepted(insert_answer, migrated_connection, session_id=session_id, word_id=word_id, selected_option=value)


@pytest.mark.parametrize("column", ["is_correct", "hint_used"])
def test_answer_with_null_flag_is_rejected(migrated_connection, session_with_word, column):
    session_id, word_id = session_with_word
    rejected(insert_answer, migrated_connection, session_id=session_id, word_id=word_id, **{column: None})


@pytest.mark.parametrize("column", ["is_correct", "hint_used"])
@pytest.mark.parametrize("value", [True, False])
def test_answer_with_boolean_flag_is_accepted(migrated_connection, session_with_word, column, value):
    session_id, word_id = session_with_word
    accepted(insert_answer, migrated_connection, session_id=session_id, word_id=word_id, **{column: value})


def test_duplicate_answer_for_same_word_in_same_session_is_rejected(migrated_connection, session_with_word):
    session_id, word_id = session_with_word
    insert_answer(migrated_connection, session_id=session_id, word_id=word_id)
    rejected(insert_answer, migrated_connection, session_id=session_id, word_id=word_id, selected_option=2)


def test_same_word_answered_in_two_sessions_is_accepted(migrated_connection, session_with_word):
    session_id, word_id = session_with_word
    insert_answer(migrated_connection, session_id=session_id, word_id=word_id)
    other = insert_session(migrated_connection)
    insert_session_word(migrated_connection, session_id=other, word_id=word_id)
    accepted(insert_answer, migrated_connection, session_id=other, word_id=word_id)


def test_answer_for_word_not_in_the_session_is_rejected(migrated_connection, session_with_word):
    session_id, _ = session_with_word
    rejected(insert_answer, migrated_connection, session_id=session_id, word_id=new_word(migrated_connection))


def test_answer_is_accepted_once_the_session_word_exists(migrated_connection, session_with_word):
    session_id, _ = session_with_word
    other_word = new_word(migrated_connection)
    rejected(insert_answer, migrated_connection, session_id=session_id, word_id=other_word)
    insert_session_word(migrated_connection, session_id=session_id, word_id=other_word, position=1)
    accepted(insert_answer, migrated_connection, session_id=session_id, word_id=other_word)


def test_answer_for_missing_session_or_word_is_rejected(migrated_connection, session_with_word):
    session_id, word_id = session_with_word
    rejected(insert_answer, migrated_connection, session_id=uuid.uuid4(), word_id=word_id)
    rejected(insert_answer, migrated_connection, session_id=session_id, word_id=uuid.uuid4())


# --- cascades and word protection ---

def build_child_with_answer(connection):
    """A child with a session, two session words and one answer. Returns (child_id, session_id, word_ids)."""
    child_id = uuid.uuid4()
    insert_child(connection, id=child_id)
    session_id = insert_session(connection, child_id=child_id)
    words = [new_word(connection), new_word(connection)]
    for position, word_id in enumerate(words):
        insert_session_word(connection, session_id=session_id, word_id=word_id, position=position)
    insert_answer(connection, session_id=session_id, word_id=words[0])
    return child_id, session_id, words


def test_deleting_a_child_removes_its_sessions_words_and_answers_only(migrated_connection):
    child_id, _, _ = build_child_with_answer(migrated_connection)
    other_child, other_session, _ = build_child_with_answer(migrated_connection)
    words_before = count(migrated_connection, "words")

    migrated_connection.execute(text("DELETE FROM children WHERE id = :id"), {"id": child_id})

    assert count(migrated_connection, "sessions", "child_id = :c", c=child_id) == 0
    assert count(migrated_connection, "session_words", "session_id IN (SELECT id FROM sessions WHERE child_id = :c)", c=child_id) == 0
    assert count(migrated_connection, "sessions") == 1
    assert count(migrated_connection, "session_words") == 2
    assert count(migrated_connection, "answers") == 1
    assert count(migrated_connection, "answers", "session_id = :s", s=other_session) == 1
    assert count(migrated_connection, "children", "id = :c", c=other_child) == 1
    assert count(migrated_connection, "words") == words_before


def test_deleting_a_child_leaves_no_rows_in_the_three_tables(migrated_connection):
    child_id, _, _ = build_child_with_answer(migrated_connection)
    migrated_connection.execute(text("DELETE FROM children WHERE id = :id"), {"id": child_id})
    assert [count(migrated_connection, t) for t in ("sessions", "session_words", "answers")] == [0, 0, 0]
    assert count(migrated_connection, "words") == 2


def test_deleting_a_session_removes_its_session_words_and_answers(migrated_connection):
    _, session_id, _ = build_child_with_answer(migrated_connection)
    _, other_session, _ = build_child_with_answer(migrated_connection)
    migrated_connection.execute(text("DELETE FROM sessions WHERE id = :id"), {"id": session_id})
    assert count(migrated_connection, "session_words", "session_id = :s", s=session_id) == 0
    assert count(migrated_connection, "answers", "session_id = :s", s=session_id) == 0
    assert count(migrated_connection, "session_words", "session_id = :s", s=other_session) == 2
    assert count(migrated_connection, "answers", "session_id = :s", s=other_session) == 1


def test_deleting_a_word_used_by_a_session_is_rejected(migrated_connection):
    _, _, words = build_child_with_answer(migrated_connection)
    with pytest.raises(IntegrityError):
        with migrated_connection.begin_nested():
            migrated_connection.execute(text("DELETE FROM words WHERE id = :id"), {"id": words[1]})


def test_deleting_an_unused_word_is_accepted(migrated_connection):
    word_id = new_word(migrated_connection)
    migrated_connection.execute(text("DELETE FROM words WHERE id = :id"), {"id": word_id})
    assert count(migrated_connection, "words", "id = :id", id=word_id) == 0
