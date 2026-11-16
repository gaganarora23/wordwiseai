"""The validator and the ``words`` table (migration 0001) agree: validated entries insert, rejected grades are rejected."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.services.vocabulary_validator import GRADES, validate_file
from tests.helpers import insert_word
from tests.test_vocabulary_validator import make_entry, write


def word_row(entry):
    """The ``words`` row for a validated entry, as the loader (#11) maps it."""
    row = {key: entry[key] for key in ("id", "word", "grade", "definition", "example", "syllables", "content_version", "explanation")}
    row["id"] = uuid.UUID(row["id"])
    for position, option in enumerate(entry["options"], start=1):
        row[f"option_{position}"] = option["text"]
    row["correct_option"] = next(i for i, option in enumerate(entry["options"], start=1) if option["correct"])
    return row


def validated(tmp_path, entry):
    assert validate_file(write(tmp_path, [entry], f"grade-{entry['grade']}.json")) == []
    return entry


def test_valid_entry_maps_to_a_words_row_and_inserts(tmp_path, db_session):
    entry = validated(tmp_path, make_entry(options=[{"text": "a", "correct": False}, {"text": "b", "correct": False}, {"text": "c", "correct": True}, {"text": "d", "correct": False}]))
    row = word_row(entry)
    assert row["correct_option"] == 3
    insert_word(db_session, **row)
    db_session.commit()
    stored = db_session.execute(text("SELECT word, option_1, option_3, correct_option FROM words")).one()
    assert tuple(stored) == ("banana", "a", "c", 3)


def test_entry_at_every_length_limit_validates_and_inserts(tmp_path, db_session):
    word = "a" * 40
    entry = validated(tmp_path, make_entry(
        word=word, syllables=word, example=word + "b" * 260, definition="d" * 300, explanation="e" * 300,
        content_version="v" * 32,
        options=[{"text": c * 150, "correct": c == "w"} for c in "wxyz"],
    ))
    insert_word(db_session, **word_row(entry))
    db_session.commit()
    assert db_session.execute(text("SELECT count(*) FROM words")).scalar_one() == 1


def test_longest_syllables_string_validates_and_inserts(tmp_path, db_session):
    parts = ["a"] * 14 + ["a" * 4]
    entry = validated(tmp_path, make_entry(word="-".join(parts), syllables=" · ".join(parts), example="-".join(parts)))
    assert len(entry["syllables"]) == 60
    insert_word(db_session, **word_row(entry))
    db_session.commit()


@pytest.mark.parametrize("grade", GRADES)
def test_every_valid_grade_validates_and_is_accepted_by_the_grade_constraint(tmp_path, db_session, grade):
    entry = validated(tmp_path, make_entry(grade=grade))
    insert_word(db_session, **word_row(entry))
    db_session.commit()


def test_there_are_13_valid_grades():
    assert len(GRADES) == 13


@pytest.mark.parametrize("grade", ["13", "0", "01", "k", "Kindergarten", "", " 1", "1 ", "-1", "1\n", "10 ", "２", "KK", "null"])
def test_validator_rejects_every_grade_value_the_constraint_rejects(tmp_path, db_session, grade):
    entry = make_entry(grade=grade)
    name = "grade-1.json"
    failures = validate_file(write(tmp_path, [entry], name))
    assert [f.field for f in failures] == ["grade"]
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            insert_word(db_session, **word_row(entry))


def test_validator_and_constraint_agree_on_each_grade_value_in_a_matching_file(tmp_path, db_session):
    for grade in [*GRADES, "13", "k", "01"]:
        entry = make_entry(grade=grade)
        name = f"grade-{grade}.json" if grade in GRADES else "grade-1.json"
        grade_failures = [f for f in validate_file(write(tmp_path, [entry], name)) if f.field == "grade"]
        try:
            with db_session.begin_nested():
                insert_word(db_session, **word_row(entry))
            db_accepts = True
        except IntegrityError:
            db_accepts = False
        assert db_accepts == (grade_failures == []), grade
    db_session.rollback()


def test_single_character_values_pass_both_the_validator_and_the_not_blank_constraints(tmp_path, db_session):
    options = [{"text": t, "correct": i == 0} for i, t in enumerate(["x", "y", "z", "w"])]
    entry = validated(tmp_path, make_entry(options=options, explanation="x"))
    insert_word(db_session, **word_row(entry))
    db_session.commit()
