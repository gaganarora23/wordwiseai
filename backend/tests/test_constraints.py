"""Database constraints of ``children`` and ``words``, checked with raw SQL on a migrated database."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

CHILD = {"nickname": "Sam", "grade": "3", "daily_goal": 5}
WORD = {
    "word": "banana", "grade": "1", "definition": "a fruit", "example": "I ate a banana.",
    "syllables": "ba · na · na", "content_version": "v1",
    "option_1": "a", "option_2": "b", "option_3": "c", "option_4": "d",
    "correct_option": 1, "explanation": "Because.",
}


def insert_child(connection, **overrides):
    values = {"id": uuid.uuid4(), **CHILD, **overrides}
    connection.execute(
        text("INSERT INTO children (id, nickname, grade, daily_goal) VALUES (:id, :nickname, :grade, :daily_goal)"),
        values,
    )


def insert_word(connection, **overrides):
    values = {"id": uuid.uuid4(), **WORD, **overrides}
    columns = ", ".join(values)
    params = ", ".join(f":{k}" for k in values)
    connection.execute(text(f"INSERT INTO words ({columns}) VALUES ({params})"), values)


def rejected(insert, connection, **overrides):
    with pytest.raises(IntegrityError):
        with connection.begin_nested():  # savepoint so the outer transaction stays usable
            insert(connection, **overrides)


def accepted(insert, connection, **overrides):
    with connection.begin_nested():
        insert(connection, **overrides)


def test_valid_child_inserts_and_timestamps_default_to_now(migrated_connection):
    insert_child(migrated_connection)
    row = migrated_connection.execute(text("SELECT created_at, updated_at FROM children")).one()
    assert row.created_at is not None and row.updated_at is not None


def test_valid_word_inserts(migrated_connection):
    insert_word(migrated_connection)
    assert migrated_connection.execute(text("SELECT count(*) FROM words")).scalar_one() == 1


@pytest.mark.parametrize("nickname", ["", "x" * 21])
def test_child_nickname_of_bad_length_is_rejected(migrated_connection, nickname):
    rejected(insert_child, migrated_connection, nickname=nickname)


@pytest.mark.parametrize("nickname", ["x", "x" * 20])
def test_child_nickname_of_boundary_length_is_accepted(migrated_connection, nickname):
    accepted(insert_child, migrated_connection, nickname=nickname)


@pytest.mark.parametrize("grade", ["13", "0", "k", "Kindergarten", ""])
def test_child_grade_outside_allowed_values_is_rejected(migrated_connection, grade):
    rejected(insert_child, migrated_connection, grade=grade)


@pytest.mark.parametrize("grade", ["K", "1", "12"])
def test_child_grade_in_allowed_values_is_accepted(migrated_connection, grade):
    accepted(insert_child, migrated_connection, grade=grade)


@pytest.mark.parametrize("goal", [0, 4, 6, 7, 15])
def test_child_daily_goal_other_than_5_or_10_is_rejected(migrated_connection, goal):
    rejected(insert_child, migrated_connection, daily_goal=goal)


@pytest.mark.parametrize("goal", [5, 10])
def test_child_daily_goal_5_or_10_is_accepted(migrated_connection, goal):
    accepted(insert_child, migrated_connection, daily_goal=goal)


@pytest.mark.parametrize("grade", ["13", "0", "k", "Kindergarten", ""])
def test_word_grade_outside_allowed_values_is_rejected(migrated_connection, grade):
    rejected(insert_word, migrated_connection, grade=grade)


@pytest.mark.parametrize("grade", ["K", "1", "12"])
def test_word_grade_in_allowed_values_is_accepted(migrated_connection, grade):
    accepted(insert_word, migrated_connection, grade=grade)


@pytest.mark.parametrize("option", ["option_1", "option_2", "option_3", "option_4"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_word_with_null_empty_or_blank_option_is_rejected(migrated_connection, option, value):
    rejected(insert_word, migrated_connection, **{option: value})


def test_word_with_fewer_than_four_options_is_rejected(migrated_connection):
    columns = [k for k in WORD if k != "option_4"]
    with pytest.raises(IntegrityError):
        with migrated_connection.begin_nested():
            migrated_connection.execute(
                text(f"INSERT INTO words (id, {', '.join(columns)}) VALUES (:id, {', '.join(':' + c for c in columns)})"),
                {"id": uuid.uuid4(), **{c: WORD[c] for c in columns}},
            )


@pytest.mark.parametrize("value", [None, 0, 5, -1])
def test_word_with_no_valid_correct_option_is_rejected(migrated_connection, value):
    rejected(insert_word, migrated_connection, correct_option=value)


@pytest.mark.parametrize("value", [1, 4])
def test_word_with_correct_option_1_to_4_is_accepted(migrated_connection, value):
    accepted(insert_word, migrated_connection, correct_option=value)


@pytest.mark.parametrize("value", [None, "", "  "])
def test_word_with_missing_or_blank_explanation_is_rejected(migrated_connection, value):
    rejected(insert_word, migrated_connection, explanation=value)


@pytest.mark.parametrize("column", ["word", "definition", "example", "syllables", "content_version"])
def test_word_missing_required_text_is_rejected(migrated_connection, column):
    rejected(insert_word, migrated_connection, **{column: None})


def test_word_id_must_be_supplied(migrated_connection):
    columns = list(WORD)
    with pytest.raises(IntegrityError):
        with migrated_connection.begin_nested():
            migrated_connection.execute(
                text(f"INSERT INTO words ({', '.join(columns)}) VALUES ({', '.join(':' + c for c in columns)})"), WORD
            )


@pytest.mark.parametrize("insert", [insert_child, insert_word])
def test_duplicate_primary_key_is_rejected(migrated_connection, insert):
    same = uuid.uuid4()
    insert(migrated_connection, id=same)
    rejected(insert, migrated_connection, id=same)
