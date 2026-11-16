"""Vocabulary ingestion (#11): validation gate, upsert, output, atomicity, errors and edge inputs.

The command-line behaviour runs as a subprocess against the harness database (real PostgreSQL).
"""

import copy
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import ConfigError
from app.services import vocabulary_ingestion as ingestion
from app.services.vocabulary_ingestion import entry_to_row, main
from tests.helpers import insert_child, insert_session_with_words, insert_word
from tests.test_vocabulary_validator import make_entry, write
from tests.test_vocabulary_validator_db import word_row

BACKEND = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND.parent / ".env"
MODULE = "app.services.vocabulary_ingestion"
NOT_MIGRATED = "Database is not migrated: run 'uv run alembic upgrade head' first"
CONFIG_MESSAGE = "DATABASE_URL must be set and start with 'postgresql+psycopg://'"


def letters(n):
    """A distinct letters-only word for every n."""
    out = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(97 + r) + out
    return "w" + out


def entry(n, grade="K", **overrides):
    word = letters(n)
    values = {
        "id": str(uuid.UUID(int=n + 1)), "word": word, "grade": grade, "example": f"I like {word}.",
        "syllables": word,
    }
    values.update(overrides)
    return make_entry(**values)


def grade_file(tmp_path, grade, entries, folder=""):
    return write(tmp_path / folder, entries, f"grade-{grade}.json")


def run_cli(args, url, env_extra=None, unset=False):
    env = {**os.environ, "DATABASE_URL": url, **(env_extra or {})}
    if unset:
        env.pop("DATABASE_URL")
    return subprocess.run([sys.executable, "-m", MODULE, *map(str, args)], cwd=BACKEND, env=env, capture_output=True, text=True)


def table(engine):
    with engine.connect() as connection:
        return [tuple(r) for r in connection.execute(text("SELECT * FROM words ORDER BY id"))]


def xmins(engine):
    with engine.connect() as connection:
        return dict(connection.execute(text("SELECT id, xmin::text FROM words")).all())


def stdout_lines(result):
    return result.stdout.splitlines()


@pytest.fixture
def files_two_grades(tmp_path):
    grade_file(tmp_path, "K", [entry(0), entry(1)])
    grade_file(tmp_path, "3", [entry(2, "3")])
    return tmp_path


# --- Mapping ---


def test_entry_maps_to_a_row_with_the_third_option_correct():
    e = make_entry(options=[{"text": t, "correct": t == "c"} for t in "abcd"])
    row = entry_to_row(e)
    assert row["correct_option"] == 3
    assert [row[f"option_{i}"] for i in range(1, 5)] == list("abcd")
    assert row == word_row(e) | {"id": e["id"]}


# --- Loading, output and idempotency ---


def test_first_run_loads_and_prints_the_exact_report(files_two_grades, clean_db, harness_db_url):
    result = run_cli([files_two_grades], harness_db_url)
    assert result.returncode == 0, result.stderr
    assert stdout_lines(result) == [
        "Grade K: 2 word(s)",
        "Grade 3: 1 word(s)",
        "Total: 3 word(s) in 2 file(s)",
        "Created: 3, updated: 0, unchanged: 0",
        "Not in files (left in place): 0",
        "Release target not reached: 3 of 650 words",
    ]
    assert result.stderr == ""
    assert len(table(clean_db)) == 3


def test_grade_lines_follow_k_then_numeric_order_not_file_order(tmp_path, clean_db, harness_db_url):
    grade_file(tmp_path, "10", [entry(0, "10")])
    grade_file(tmp_path, "2", [entry(1, "2")])
    grade_file(tmp_path, "K", [entry(2)])
    result = run_cli([tmp_path], harness_db_url)
    assert stdout_lines(result)[:3] == ["Grade K: 1 word(s)", "Grade 2: 1 word(s)", "Grade 10: 1 word(s)"]


def test_second_run_changes_nothing_and_reports_all_unchanged(files_two_grades, clean_db, harness_db_url):
    run_cli([files_two_grades], harness_db_url)
    before, versions = table(clean_db), xmins(clean_db)
    result = run_cli([files_two_grades], harness_db_url)
    assert result.returncode == 0
    assert "Created: 0, updated: 0, unchanged: 3" in stdout_lines(result)
    assert table(clean_db) == before
    assert xmins(clean_db) == versions  # no UPDATE was issued


def test_loaded_rows_equal_the_file_values(files_two_grades, clean_db, harness_db_url):
    run_cli([files_two_grades], harness_db_url)
    with clean_db.connect() as connection:
        stored = connection.execute(text("SELECT * FROM words WHERE word = :w"), {"w": letters(0)}).mappings().one()
    assert dict(stored) == word_row(entry(0))


def test_only_changed_file_rows_are_updated_on_rerun(files_two_grades, clean_db, harness_db_url):
    run_cli([files_two_grades], harness_db_url)
    versions = xmins(clean_db)
    grade_file(files_two_grades, "K", [entry(0, definition="New meaning."), entry(1)])
    result = run_cli([files_two_grades], harness_db_url)
    assert "Created: 0, updated: 1, unchanged: 2" in stdout_lines(result)
    after = xmins(clean_db)
    changed = [i for i in versions if versions[i] != after[i]]
    assert changed == [uuid.UUID(int=1)]


CHANGES = {
    "definition": {"definition": "Something else entirely."},
    "example": {"example": "A new banana sentence for banana."},
    "syllables": {"syllables": "ban · ana"},
    "content_version": {"content_version": "2027.2"},
    "explanation": {"explanation": "A different explanation."},
    "word": {"word": "Banana", "example": "I ate a Banana.", "syllables": "Ba · na · na"},
}


@pytest.mark.parametrize("column", CHANGES)
def test_changing_one_column_updates_that_row_in_place(tmp_path, clean_db, harness_db_url, column):
    base = make_entry(id=str(uuid.UUID(int=7)))
    grade_file(tmp_path, "K", [base])
    run_cli([tmp_path], harness_db_url)
    grade_file(tmp_path, "K", [{**base, **CHANGES[column]}])
    result = run_cli([tmp_path], harness_db_url)
    assert "Created: 0, updated: 1, unchanged: 0" in stdout_lines(result)
    with clean_db.connect() as connection:
        rows = connection.execute(text(f"SELECT {column} FROM words")).all()
    assert rows == [(CHANGES[column][column],)]


@pytest.mark.parametrize("index", range(4))
def test_changing_one_option_text_updates_the_row(tmp_path, clean_db, harness_db_url, index):
    base = make_entry()
    grade_file(tmp_path, "K", [base])
    run_cli([tmp_path], harness_db_url)
    changed = copy.deepcopy(base)
    changed["options"][index]["text"] = "Brand new option text"
    grade_file(tmp_path, "K", [changed])
    assert "updated: 1" in run_cli([tmp_path], harness_db_url).stdout
    with clean_db.connect() as connection:
        assert connection.execute(text(f"SELECT option_{index + 1} FROM words")).scalar_one() == "Brand new option text"


def test_changing_which_option_is_correct_updates_correct_option(tmp_path, clean_db, harness_db_url):
    base = make_entry()
    grade_file(tmp_path, "K", [base])
    run_cli([tmp_path], harness_db_url)
    changed = copy.deepcopy(base)
    changed["options"][0]["correct"], changed["options"][3]["correct"] = False, True
    grade_file(tmp_path, "K", [changed])
    assert "updated: 1" in run_cli([tmp_path], harness_db_url).stdout
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT correct_option FROM words")).scalar_one() == 4


def test_moving_an_entry_to_another_grade_file_updates_its_grade(tmp_path, clean_db, harness_db_url):
    e = entry(0, "3")
    grade_file(tmp_path, "3", [e])
    run_cli([tmp_path], harness_db_url)
    (tmp_path / "grade-3.json").unlink()
    grade_file(tmp_path, "4", [{**e, "grade": "4"}])
    result = run_cli([tmp_path], harness_db_url)
    assert "Created: 0, updated: 1, unchanged: 0" in stdout_lines(result)
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT id, grade FROM words")).all() == [(uuid.UUID(e["id"]), "4")]


def test_rows_are_matched_by_id_not_by_word_text(tmp_path, clean_db, harness_db_url, db_session):
    existing = insert_word(db_session, word=letters(0), grade="K")
    db_session.commit()
    new_id = str(uuid.UUID(int=500))
    grade_file(tmp_path, "K", [entry(0, id=new_id)])  # same word text, new id
    result = run_cli([tmp_path], harness_db_url)
    assert "Created: 1, updated: 0, unchanged: 0" in stdout_lines(result)
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM words WHERE word = :w"), {"w": letters(0)}).scalar_one() == 2
    # an existing id with different word text is updated, not duplicated
    grade_file(tmp_path, "K", [entry(0, id=str(existing), word="renamed", example="A renamed one.", syllables="renamed")])
    result = run_cli([tmp_path], harness_db_url)
    assert "updated: 1" in result.stdout
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT word FROM words WHERE id = :i"), {"i": existing}).scalar_one() == "renamed"


def test_updating_a_referenced_word_keeps_its_history(tmp_path, clean_db, harness_db_url, db_session):
    word_id = insert_word(db_session, word=letters(0), grade="1", definition="old")
    child_id = insert_child(db_session)
    session_id = insert_session_with_words(db_session, child_id=child_id, word_ids=[word_id])
    db_session.execute(
        text("INSERT INTO answers (session_id, word_id, selected_option, is_correct, hint_used) VALUES (:s, :w, 1, true, false)"),
        {"s": session_id, "w": word_id},
    )
    db_session.execute(text("INSERT INTO word_mastery (child_id, word_id) VALUES (:c, :w)"), {"c": child_id, "w": word_id})
    db_session.commit()

    def history():
        with clean_db.connect() as connection:
            return [
                [tuple(r) for r in connection.execute(text(f"SELECT * FROM {name} ORDER BY 1, 2"))]
                for name in ("session_words", "answers", "word_mastery")
            ]

    before = history()
    assert all(len(rows) == 1 for rows in before)
    grade_file(tmp_path, "1", [entry(0, "1", id=str(word_id), definition="A fresh definition.")])
    result = run_cli([tmp_path], harness_db_url)
    assert "Created: 0, updated: 1, unchanged: 0" in stdout_lines(result), result.stderr
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT definition FROM words WHERE id = :i"), {"i": word_id}).scalar_one() == "A fresh definition."
    assert history() == before


# --- Words not in the files ---


def test_words_not_in_files_survive_with_references_and_are_reported(tmp_path, clean_db, harness_db_url, db_session):
    kept = insert_word(db_session, word="zebra", grade="2")
    kept_k = insert_word(db_session, word="apple", grade="K")
    insert_session_with_words(db_session, word_ids=[kept])
    db_session.commit()
    before = table(clean_db)
    grade_file(tmp_path, "K", [entry(0)])
    result = run_cli([tmp_path], harness_db_url)
    assert result.returncode == 0, result.stderr
    lines = stdout_lines(result)
    block = lines.index("Not in files (left in place): 2")
    assert lines[block + 1:block + 3] == [f"  {kept_k} apple (grade K)", f"  {kept} zebra (grade 2)"]
    assert lines[-1].startswith("Release target not reached")
    assert [r for r in table(clean_db) if r[0] in (kept, kept_k)] == [r for r in before if r[0] in (kept, kept_k)]
    with clean_db.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM session_words WHERE word_id = :w"), {"w": kept}).scalar_one() == 1


def test_rerun_with_fewer_files_keeps_the_other_grades(files_two_grades, clean_db, harness_db_url):
    run_cli([files_two_grades], harness_db_url)
    before = table(clean_db)
    result = run_cli([files_two_grades / "grade-K.json"], harness_db_url)
    assert result.returncode == 0
    assert "Not in files (left in place): 1" in stdout_lines(result)
    assert table(clean_db) == before


# --- Target line ---


@pytest.mark.parametrize(("count", "line"), [
    (649, "Release target not reached: 649 of 650 words"),
    (650, "Release target reached: 650 words"),
    (651, "Release target not reached: 651 of 650 words"),
])
def test_target_line_counts_entries_in_the_files(tmp_path, clean_db, harness_db_url, count, line):
    grade_file(tmp_path, "K", [entry(n) for n in range(count)])
    result = run_cli([tmp_path], harness_db_url)
    assert result.returncode == 0, result.stderr
    assert stdout_lines(result)[-1] == line
    assert f"Total: {count} word(s) in 1 file(s)" in stdout_lines(result)
    if count != 650:
        assert "reached" not in line.replace("not reached", "")


def test_target_counts_files_not_database_rows(tmp_path, clean_db, harness_db_url, db_session):
    for n in range(1, 4):
        insert_word(db_session, word=f"old{'x' * n}")
    db_session.commit()
    grade_file(tmp_path, "K", [entry(0)])
    assert stdout_lines(run_cli([tmp_path], harness_db_url))[-1] == "Release target not reached: 1 of 650 words"


def test_same_word_in_two_grade_files_is_not_an_error(tmp_path, clean_db, harness_db_url):
    grade_file(tmp_path, "K", [entry(0)])
    grade_file(tmp_path, "1", [entry(1, "1", word=letters(0), example=f"I like {letters(0)}.", syllables=letters(0))])
    result = run_cli([tmp_path], harness_db_url)
    assert result.returncode == 0, result.stderr
    assert len(table(clean_db)) == 2


def test_folder_named_fixtures_is_loaded_like_any_other(tmp_path, clean_db, harness_db_url):
    grade_file(tmp_path, "K", [entry(0)], folder="fixtures")
    assert run_cli([tmp_path], harness_db_url).returncode == 0
    assert len(table(clean_db)) == 1


# --- Validation gate ---


def test_invalid_file_loads_nothing_and_leaves_existing_rows_unchanged(files_two_grades, clean_db, harness_db_url, db_session):
    insert_word(db_session)
    db_session.commit()
    grade_file(files_two_grades, "5", [entry(9, "5", definition="")])
    before = table(clean_db)
    result = run_cli([files_two_grades], harness_db_url)
    assert result.returncode == 1
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert lines[-1] == "FAILED: 1 failure(s) in 1 file(s)"
    assert "definition: must not be blank" in lines[0]
    assert table(clean_db) == before


def test_valid_files_in_a_mixed_directory_write_nothing(files_two_grades, clean_db, harness_db_url):
    grade_file(files_two_grades, "7", [entry(8, "8")])
    assert run_cli([files_two_grades], harness_db_url).returncode == 1
    assert table(clean_db) == []


def test_cross_file_duplicate_ids_are_caught(tmp_path, clean_db, harness_db_url):
    grade_file(tmp_path, "K", [entry(0)])
    grade_file(tmp_path, "1", [entry(1, "1", id=entry(0)["id"])])
    result = run_cli([tmp_path], harness_db_url)
    assert result.returncode == 1
    assert "duplicate id" in result.stderr
    assert table(clean_db) == []


def test_failure_lines_equal_the_validator_output(files_two_grades, harness_db_url):
    grade_file(files_two_grades, "5", [entry(9, "5", definition="")])
    validator = subprocess.run(
        [sys.executable, "-m", "app.services.vocabulary_validator", str(files_two_grades)],
        cwd=BACKEND, capture_output=True, text=True,
    )
    result = run_cli([files_two_grades], harness_db_url)
    assert result.stderr == validator.stderr and result.returncode == validator.returncode == 1


def test_invalid_file_exits_1_not_3_without_database_url(tmp_path):
    grade_file(tmp_path, "K", [entry(0, definition="")])
    result = run_cli([tmp_path], "", unset=True)
    assert result.returncode == 1
    assert "FAILED: 1 failure(s) in 1 file(s)" in result.stderr


def test_invalid_file_opens_no_database_connection(tmp_path, monkeypatch, capsys):
    grade_file(tmp_path, "K", [entry(0, definition="")])
    monkeypatch.setattr(ingestion, "ingest", lambda rows: pytest.fail("the database was contacted"))
    assert main([str(tmp_path)]) == 1


# --- Atomicity ---


def test_error_partway_rolls_back_the_whole_run(tmp_path, clean_db, harness_db_url, db_session):
    existing = insert_word(db_session, word=letters(0), definition="old")
    db_session.commit()
    grade_file(tmp_path, "K", [entry(0, id=str(existing), definition="new"), entry(1), entry(2, word="boom", example="A boom.", syllables="boom"), entry(3)])
    before = table(clean_db)
    with clean_db.begin() as connection:
        connection.execute(text(
            "CREATE FUNCTION fail_on_boom() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN "
            "IF NEW.word = 'boom' THEN RAISE EXCEPTION 'boom is rejected'; END IF; RETURN NEW; END $$"))
        connection.execute(text("CREATE TRIGGER fail_on_boom BEFORE INSERT ON words FOR EACH ROW EXECUTE FUNCTION fail_on_boom()"))
    try:
        result = run_cli([tmp_path], harness_db_url)
    finally:
        with clean_db.begin() as connection:
            connection.execute(text("DROP TRIGGER fail_on_boom ON words"))
            connection.execute(text("DROP FUNCTION fail_on_boom()"))
    assert result.returncode == 3
    assert result.stdout == ""
    assert result.stderr.strip() == "Database error, nothing was loaded: boom is rejected"
    assert "Traceback" not in result.stderr
    assert table(clean_db) == before  # the update of row 0 and the insert of row 1 are rolled back


def test_error_on_third_row_in_process_rolls_back_earlier_rows(tmp_path, clean_db, harness_db_url, monkeypatch, capsys):
    grade_file(tmp_path, "K", [entry(n) for n in range(5)])
    real, calls = ingestion.upsert_word, []

    def failing(connection, row):
        calls.append(row)
        if len(calls) == 3:
            raise SQLAlchemyError("forced failure")
        return real(connection, row)

    monkeypatch.setenv("DATABASE_URL", harness_db_url)
    monkeypatch.setattr(ingestion, "upsert_word", failing)
    from app import db

    db.get_engine.cache_clear()
    db.get_settings.cache_clear()
    try:
        assert main([str(tmp_path)]) == 3
    finally:
        db.get_engine.cache_clear()
        db.get_settings.cache_clear()
    captured = capsys.readouterr()
    assert captured.err.strip() == "Database error, nothing was loaded: forced failure"
    assert len(calls) == 3
    assert table(clean_db) == []


# --- Database errors ---


def test_unset_database_url_prints_the_config_error(tmp_path):
    if ENV_FILE.exists():
        pytest.skip("a repo-root .env would supply DATABASE_URL; the empty-value test covers the same path")
    grade_file(tmp_path, "K", [entry(0)])
    result = run_cli([tmp_path], "", unset=True)
    assert (result.returncode, result.stdout, result.stderr.strip()) == (3, "", CONFIG_MESSAGE)


def test_empty_database_url_prints_the_config_error(tmp_path):
    grade_file(tmp_path, "K", [entry(0)])
    result = run_cli([tmp_path], "")
    assert (result.returncode, result.stdout, result.stderr.strip()) == (3, "", CONFIG_MESSAGE)


def test_wrong_scheme_is_rejected_without_echoing_the_url(tmp_path):
    grade_file(tmp_path, "K", [entry(0)])
    result = run_cli([tmp_path], "mysql://user:s3cretpw@localhost/db")
    assert result.returncode == 3
    assert result.stderr.strip() == CONFIG_MESSAGE
    assert "s3cretpw" not in result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_unreachable_database_is_one_line_without_secrets(tmp_path):
    grade_file(tmp_path, "K", [entry(0)])
    result = run_cli([tmp_path], "postgresql+psycopg://wordwise:s3cretpw@127.0.0.1:1/wordwise")
    assert result.returncode == 3
    lines = result.stderr.splitlines()
    assert len(lines) == 1 and lines[0].startswith("Cannot connect to the database")
    assert "s3cretpw" not in result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_unmigrated_database_is_reported_and_nothing_is_created(tmp_path, throwaway_db_url):
    from sqlalchemy import create_engine, inspect

    grade_file(tmp_path, "K", [entry(0)])
    result = run_cli([tmp_path], throwaway_db_url)
    assert result.returncode == 3
    assert result.stderr.strip() == NOT_MIGRATED
    assert result.stdout == ""
    engine = create_engine(throwaway_db_url)
    try:
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()


def test_config_error_is_turned_into_exit_3(tmp_path, monkeypatch, capsys):
    grade_file(tmp_path, "K", [entry(0)])

    def raise_config_error():
        raise ConfigError(CONFIG_MESSAGE)

    monkeypatch.setattr(ingestion, "load_settings", raise_config_error)
    assert main([str(tmp_path)]) == 3
    assert capsys.readouterr().err.strip() == CONFIG_MESSAGE


# --- Empty and edge inputs ---


def test_empty_directory_exits_2_before_reading_settings(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = run_cli([empty], "")  # invalid settings would exit 3 if they were read
    assert (result.returncode, result.stdout, result.stderr.strip()) == (2, "", f"no JSON files found in {empty}")


def test_directory_with_only_a_readme_exits_2(tmp_path, clean_db, harness_db_url):
    (tmp_path / "README.md").write_text("# data\n")
    result = run_cli([tmp_path], harness_db_url)
    assert (result.returncode, result.stderr.strip()) == (2, f"no JSON files found in {tmp_path}")
    assert table(clean_db) == []


def test_missing_path_exits_2(tmp_path):
    missing = tmp_path / "nope"
    result = run_cli([missing], "")
    assert (result.returncode, result.stderr.strip()) == (2, f"no JSON files found: {missing} does not exist")


def test_default_path_is_the_data_folder_next_to_the_module(clean_db, harness_db_url):
    default = subprocess.run([sys.executable, "-m", "app.services.vocabulary_validator"], cwd=BACKEND, capture_output=True, text=True)
    result = run_cli([], harness_db_url)
    elsewhere = subprocess.run(
        [sys.executable, "-m", MODULE], cwd=BACKEND / "app", capture_output=True, text=True,
        env={**os.environ, "DATABASE_URL": harness_db_url, "PYTHONPATH": str(BACKEND)},
    )
    assert result.returncode == elsewhere.returncode == default.returncode
    assert result.stderr == elsewhere.stderr


def test_file_with_an_empty_array_is_a_validation_failure(tmp_path, clean_db, harness_db_url):
    path = write(tmp_path, [], "grade-K.json")
    result = run_cli([path], harness_db_url)
    assert result.returncode == 1
    assert f"{path}: file: no entries" in result.stderr


def test_usage_error_exits_2():
    result = run_cli(["--no-such-flag"], "")
    assert result.returncode == 2


def test_help_states_removed_words_650_rule_and_database_url():
    result = run_cli(["--help"], "")
    assert result.returncode == 0
    for phrase in ("never deleted or changed", "650", "DATABASE_URL", ".env"):
        assert phrase in result.stdout
