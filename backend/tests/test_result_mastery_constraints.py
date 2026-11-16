"""Database constraints of ``quiz_results`` and ``word_mastery``, checked with raw SQL on a migrated database."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_constraints import accepted, insert_child, rejected
from tests.test_session_constraints import count, insert_session, insert_session_word, new_word

NOW = "2026-01-01T00:00:00+00:00"


def insert_result(connection, **overrides):
    """Insert a quiz result; creates the session unless ``session_id`` is given. Counts default to 3 correct, 2 incorrect."""
    values = {"correct_count": 3, "incorrect_count": 2, **overrides}
    values.setdefault("score", values["correct_count"])
    if "review_word_ids" not in values:
        values["review_word_ids"] = ids(values["incorrect_count"])  # exactly the missed words
    if "session_id" not in values:
        values["session_id"] = insert_session(connection)
    connection.execute(
        text(
            "INSERT INTO quiz_results (session_id, score, correct_count, incorrect_count, review_word_ids) "
            "VALUES (:session_id, :score, :correct_count, :incorrect_count, CAST(:review_word_ids AS uuid[]))"
        ),
        {**values, "review_word_ids": array_literal(values["review_word_ids"])},
    )
    return values["session_id"]


def array_literal(ids):
    """A PostgreSQL array literal; ``None`` elements are written as NULL and ``None`` itself stays NULL."""
    if ids is None:
        return None
    return "{" + ",".join("NULL" if i is None else str(i) for i in ids) + "}"


def ids(n):
    return [uuid.uuid4() for _ in range(n)]


def insert_mastery(connection, **overrides):
    """Insert a word_mastery row with every column given (NEW defaults); creates the child and word unless given."""
    values = {
        "status": "NEW", "consecutive_correct": 0, "last_practiced_at": None, "needs_review": False, **overrides,
    }
    if "child_id" not in values:
        values["child_id"] = uuid.uuid4()
        insert_child(connection, id=values["child_id"])
    if "word_id" not in values:
        values["word_id"] = new_word(connection)
    columns = ", ".join(values)
    params = ", ".join(f":{k}" for k in values)
    connection.execute(text(f"INSERT INTO word_mastery ({columns}) VALUES ({params})"), values)
    return values["child_id"], values["word_id"]


# --- word_mastery: primary key ---

def test_second_mastery_row_for_same_child_and_word_is_rejected(migrated_connection):
    child_id, word_id = insert_mastery(migrated_connection)
    rejected(insert_mastery, migrated_connection, child_id=child_id, word_id=word_id)


def test_same_word_for_a_different_child_is_accepted(migrated_connection):
    _, word_id = insert_mastery(migrated_connection)
    accepted(insert_mastery, migrated_connection, word_id=word_id)


def test_different_word_for_the_same_child_is_accepted(migrated_connection):
    child_id, _ = insert_mastery(migrated_connection)
    accepted(insert_mastery, migrated_connection, child_id=child_id)


# --- word_mastery: defaults ---

def test_inserting_only_child_and_word_gives_new_zero_never_practiced_no_review(migrated_connection):
    child_id = uuid.uuid4()
    insert_child(migrated_connection, id=child_id)
    word_id = new_word(migrated_connection)
    migrated_connection.execute(
        text("INSERT INTO word_mastery (child_id, word_id) VALUES (:c, :w)"), {"c": child_id, "w": word_id}
    )
    row = migrated_connection.execute(
        text("SELECT status, consecutive_correct, last_practiced_at, needs_review FROM word_mastery")
    ).one()
    assert (row.status, row.consecutive_correct, row.last_practiced_at, row.needs_review) == ("NEW", 0, None, False)


# --- word_mastery: status ---

@pytest.mark.parametrize("value", [None, "", "new", "Learning", " NEW", "MASTERED ", "NEEDS_REVIEW", "done"])
def test_mastery_status_outside_allowed_values_is_rejected(migrated_connection, value):
    rejected(insert_mastery, migrated_connection, status=value, last_practiced_at=NOW)


@pytest.mark.parametrize("status,streak,practiced", [("NEW", 0, None), ("LEARNING", 1, NOW), ("MASTERED", 3, NOW)])
def test_mastery_status_in_allowed_values_is_accepted(migrated_connection, status, streak, practiced):
    accepted(insert_mastery, migrated_connection, status=status, consecutive_correct=streak, last_practiced_at=practiced)


def test_all_new_constraints_exist_under_their_explicit_names(migrated_connection):
    names = set(migrated_connection.execute(text(
        "SELECT conname FROM pg_constraint WHERE conrelid IN ('quiz_results'::regclass, 'word_mastery'::regclass) AND contype IN ('p', 'f', 'c')"
    )).scalars())
    assert names == {
        "pk_quiz_results", "fk_quiz_results_session_id_sessions", "ck_quiz_results_counts_valid",
        "ck_quiz_results_score_valid", "ck_quiz_results_review_word_ids_no_nulls", "ck_quiz_results_review_word_ids_length",
        "pk_word_mastery", "fk_word_mastery_child_id_children", "fk_word_mastery_word_id_words",
        "ck_word_mastery_status_valid", "ck_word_mastery_consecutive_correct_valid", "ck_word_mastery_status_progress",
    }


# --- word_mastery: consecutive_correct ---

@pytest.mark.parametrize("value", [-1, 4, None])
def test_mastery_streak_outside_0_to_3_is_rejected(migrated_connection, value):
    rejected(insert_mastery, migrated_connection, status="LEARNING", consecutive_correct=value, last_practiced_at=NOW)


def test_mastery_streak_4_is_rejected_by_the_named_streak_constraint(migrated_connection):
    with pytest.raises(IntegrityError, match="ck_word_mastery_consecutive_correct_valid"):
        with migrated_connection.begin_nested():
            insert_mastery(migrated_connection, status="MASTERED", consecutive_correct=4, last_practiced_at=NOW)


@pytest.mark.parametrize("value", [0, 1, 2, 3])
def test_mastery_streak_0_to_3_is_accepted(migrated_connection, value):
    status = "MASTERED" if value == 3 else "LEARNING"
    accepted(insert_mastery, migrated_connection, status=status, consecutive_correct=value, last_practiced_at=NOW)


# --- word_mastery: status and progress agree ---

VALID_PROGRESS = [
    ("NEW", 0, None, False),
    ("LEARNING", 0, NOW, False),
    ("LEARNING", 1, NOW, False),
    ("LEARNING", 2, NOW, False),
    ("LEARNING", 0, NOW, True),
    ("LEARNING", 2, NOW, True),
    ("MASTERED", 3, NOW, False),
    ("MASTERED", 3, NOW, True),
]
INVALID_PROGRESS = [
    ("NEW", 1, None, False),
    ("NEW", 3, None, False),
    ("NEW", 0, None, True),
    ("NEW", 0, NOW, False),
    ("NEW", 0, NOW, True),
    ("LEARNING", 3, NOW, False),
    ("LEARNING", 3, NOW, True),
    ("LEARNING", 0, None, False),
    ("LEARNING", 2, None, True),
    ("MASTERED", 0, NOW, False),
    ("MASTERED", 2, NOW, False),
    ("MASTERED", 2, NOW, True),
    ("MASTERED", 3, None, False),
    ("MASTERED", 3, None, True),
]


@pytest.mark.parametrize("status,streak,practiced,review", VALID_PROGRESS)
def test_status_with_matching_progress_is_accepted(migrated_connection, status, streak, practiced, review):
    accepted(insert_mastery, migrated_connection, status=status, consecutive_correct=streak,
             last_practiced_at=practiced, needs_review=review)


@pytest.mark.parametrize("status,streak,practiced,review", INVALID_PROGRESS)
def test_status_with_mismatched_progress_is_rejected(migrated_connection, status, streak, practiced, review):
    rejected(insert_mastery, migrated_connection, status=status, consecutive_correct=streak,
             last_practiced_at=practiced, needs_review=review)


def test_mismatched_progress_is_rejected_by_the_named_progress_constraint(migrated_connection):
    with pytest.raises(IntegrityError, match="ck_word_mastery_status_progress"):
        with migrated_connection.begin_nested():
            insert_mastery(migrated_connection, status="MASTERED", consecutive_correct=2, last_practiced_at=NOW)


def test_updating_a_mastered_row_to_streak_2_without_changing_status_is_rejected(migrated_connection):
    child_id, word_id = insert_mastery(migrated_connection, status="MASTERED", consecutive_correct=3, last_practiced_at=NOW)
    with pytest.raises(IntegrityError):
        with migrated_connection.begin_nested():
            migrated_connection.execute(
                text("UPDATE word_mastery SET consecutive_correct = 2 WHERE child_id = :c AND word_id = :w"),
                {"c": child_id, "w": word_id},
            )


# --- word_mastery: needs_review ---

def test_mastery_needs_review_null_is_rejected(migrated_connection):
    rejected(insert_mastery, migrated_connection, status="LEARNING", last_practiced_at=NOW, needs_review=None)


@pytest.mark.parametrize("status,streak", [("LEARNING", 1), ("MASTERED", 3)])
def test_needs_review_with_learning_or_mastered_status_is_accepted(migrated_connection, status, streak):
    accepted(insert_mastery, migrated_connection, status=status, consecutive_correct=streak,
             last_practiced_at=NOW, needs_review=True)
    assert migrated_connection.execute(
        text("SELECT status, needs_review FROM word_mastery")
    ).one() == (status, True)


# --- word_mastery: foreign keys ---

def test_mastery_for_missing_child_is_rejected(migrated_connection):
    rejected(insert_mastery, migrated_connection, child_id=uuid.uuid4())


def test_mastery_for_missing_word_is_rejected(migrated_connection):
    rejected(insert_mastery, migrated_connection, word_id=uuid.uuid4())


# --- quiz_results: primary key and foreign key ---

def test_second_result_for_the_same_session_is_rejected(migrated_connection):
    session_id = insert_result(migrated_connection)
    rejected(insert_result, migrated_connection, session_id=session_id)


def test_results_for_two_different_sessions_are_accepted(migrated_connection):
    insert_result(migrated_connection)
    accepted(insert_result, migrated_connection)
    assert count(migrated_connection, "quiz_results") == 2


def test_result_for_a_missing_session_is_rejected(migrated_connection):
    rejected(insert_result, migrated_connection, session_id=uuid.uuid4())


def test_result_defaults_review_word_ids_to_empty_and_created_at_to_now(migrated_connection):
    session_id = insert_session(migrated_connection)
    migrated_connection.execute(
        text("INSERT INTO quiz_results (session_id, score, correct_count, incorrect_count) VALUES (:s, 4, 4, 0)"),
        {"s": session_id},
    )
    row = migrated_connection.execute(text("SELECT review_word_ids, created_at FROM quiz_results")).one()
    assert row.review_word_ids == [] and row.created_at is not None


# --- quiz_results: counts ---

@pytest.mark.parametrize("column", ["correct_count", "incorrect_count"])
def test_negative_count_is_rejected(migrated_connection, column):
    # Keep the sum in 1..10 so only the non-negative rule can fail.
    correct, incorrect = (-1, 5) if column == "correct_count" else (5, -1)
    rejected(insert_result, migrated_connection, correct_count=correct, incorrect_count=incorrect,
             score=correct, review_word_ids=[])


@pytest.mark.parametrize("column", ["correct_count", "incorrect_count"])
def test_count_of_zero_is_accepted(migrated_connection, column):
    correct = 0 if column == "correct_count" else 5
    incorrect = 0 if column == "incorrect_count" else 5
    accepted(insert_result, migrated_connection, correct_count=correct, incorrect_count=incorrect,
             review_word_ids=ids(incorrect))


@pytest.mark.parametrize("correct,incorrect", [(0, 0), (6, 5), (11, 0), (0, 11)])
def test_counts_summing_outside_1_to_10_are_rejected(migrated_connection, correct, incorrect):
    rejected(insert_result, migrated_connection, correct_count=correct, incorrect_count=incorrect,
             review_word_ids=ids(incorrect))


@pytest.mark.parametrize("correct,incorrect", [(1, 0), (0, 1), (10, 0), (7, 3), (0, 10)])
def test_counts_summing_to_1_or_10_are_accepted(migrated_connection, correct, incorrect):
    accepted(insert_result, migrated_connection, correct_count=correct, incorrect_count=incorrect,
             review_word_ids=ids(incorrect))


@pytest.mark.parametrize("column", ["score", "correct_count", "incorrect_count"])
def test_null_number_in_a_result_is_rejected(migrated_connection, column):
    rejected(insert_result, migrated_connection, review_word_ids=[], **{column: None})


# --- quiz_results: score ---

def test_score_equal_to_correct_count_is_accepted(migrated_connection):
    accepted(insert_result, migrated_connection, correct_count=3, incorrect_count=2, score=3)


@pytest.mark.parametrize("score", [2, 4])
def test_score_different_from_correct_count_is_rejected(migrated_connection, score):
    rejected(insert_result, migrated_connection, correct_count=3, incorrect_count=2, score=score)


def test_score_rejection_is_by_the_named_score_constraint(migrated_connection):
    with pytest.raises(IntegrityError, match="ck_quiz_results_score_valid"):
        with migrated_connection.begin_nested():
            insert_result(migrated_connection, correct_count=3, incorrect_count=2, score=4)


# --- quiz_results: review_word_ids ---

def test_null_review_word_ids_is_rejected(migrated_connection):
    rejected(insert_result, migrated_connection, review_word_ids=None)


def test_empty_review_word_ids_is_accepted_when_nothing_was_missed(migrated_connection):
    accepted(insert_result, migrated_connection, correct_count=5, incorrect_count=0, review_word_ids=[])


@pytest.mark.parametrize("review_word_ids", [[None], [None, uuid.uuid4()], [uuid.uuid4(), uuid.uuid4(), None]])
def test_review_word_ids_with_a_null_element_is_rejected(migrated_connection, review_word_ids):
    # incorrect_count equals the array length, so only the NULL element can make the row invalid.
    rejected(insert_result, migrated_connection, correct_count=3, incorrect_count=len(review_word_ids),
             review_word_ids=review_word_ids)


@pytest.mark.parametrize("length", [1, 6, 0, 10])
def test_review_word_ids_length_outside_missed_to_total_is_rejected(migrated_connection, length):
    rejected(insert_result, migrated_connection, correct_count=3, incorrect_count=2, review_word_ids=ids(length))


@pytest.mark.parametrize("length", [2, 3, 5])
def test_review_word_ids_length_between_missed_and_total_is_accepted(migrated_connection, length):
    accepted(insert_result, migrated_connection, correct_count=3, incorrect_count=2, review_word_ids=ids(length))


def test_review_word_ids_length_rejection_is_by_a_named_result_constraint(migrated_connection):
    with pytest.raises(IntegrityError, match="ck_quiz_results_review_word_ids_length"):
        with migrated_connection.begin_nested():
            insert_result(migrated_connection, correct_count=3, incorrect_count=2, review_word_ids=ids(6))


def test_review_word_ids_with_null_element_is_rejected_by_the_named_constraint(migrated_connection):
    with pytest.raises(IntegrityError, match="ck_quiz_results_review_word_ids_no_nulls"):
        with migrated_connection.begin_nested():
            insert_result(migrated_connection, correct_count=3, incorrect_count=2, review_word_ids=[None, uuid.uuid4()])


# --- cascades and word protection ---

def build_child_with_result_and_mastery(connection):
    """A child with a session, a result and two mastery rows. Returns (child_id, session_id, word_ids)."""
    child_id = uuid.uuid4()
    insert_child(connection, id=child_id)
    session_id = insert_session(connection, child_id=child_id, status="completed", completed_at=NOW)
    insert_result(connection, session_id=session_id)
    words = [new_word(connection), new_word(connection)]
    for word_id in words:
        insert_mastery(connection, child_id=child_id, word_id=word_id)
    return child_id, session_id, words


def test_deleting_a_child_removes_its_sessions_results_and_mastery_only(migrated_connection):
    child_id, _, _ = build_child_with_result_and_mastery(migrated_connection)
    other_child, other_session, _ = build_child_with_result_and_mastery(migrated_connection)
    words_before = count(migrated_connection, "words")

    migrated_connection.execute(text("DELETE FROM children WHERE id = :id"), {"id": child_id})

    assert count(migrated_connection, "sessions", "child_id = :c", c=child_id) == 0
    assert count(migrated_connection, "word_mastery", "child_id = :c", c=child_id) == 0
    assert [count(migrated_connection, t) for t in ("sessions", "quiz_results", "word_mastery")] == [1, 1, 2]
    assert count(migrated_connection, "quiz_results", "session_id = :s", s=other_session) == 1
    assert count(migrated_connection, "word_mastery", "child_id = :c", c=other_child) == 2
    assert count(migrated_connection, "words") == words_before


def test_deleting_a_session_removes_its_result_but_keeps_the_childs_mastery(migrated_connection):
    child_id, session_id, _ = build_child_with_result_and_mastery(migrated_connection)
    _, other_session, _ = build_child_with_result_and_mastery(migrated_connection)

    migrated_connection.execute(text("DELETE FROM sessions WHERE id = :id"), {"id": session_id})

    assert count(migrated_connection, "quiz_results", "session_id = :s", s=session_id) == 0
    assert count(migrated_connection, "quiz_results", "session_id = :s", s=other_session) == 1
    assert count(migrated_connection, "word_mastery", "child_id = :c", c=child_id) == 2
    assert count(migrated_connection, "children", "id = :c", c=child_id) == 1


def test_deleting_a_word_with_a_mastery_row_is_rejected_until_the_row_is_deleted(migrated_connection):
    child_id, word_id = insert_mastery(migrated_connection)
    with pytest.raises(IntegrityError):
        with migrated_connection.begin_nested():
            migrated_connection.execute(text("DELETE FROM words WHERE id = :id"), {"id": word_id})
    assert count(migrated_connection, "words", "id = :id", id=word_id) == 1

    migrated_connection.execute(text("DELETE FROM word_mastery WHERE child_id = :c AND word_id = :w"), {"c": child_id, "w": word_id})
    migrated_connection.execute(text("DELETE FROM words WHERE id = :id"), {"id": word_id})
    assert count(migrated_connection, "words", "id = :id", id=word_id) == 0
