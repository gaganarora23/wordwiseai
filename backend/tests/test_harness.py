"""Proofs that the integration harness (conftest.py, harness.py, helpers.py) isolates and cleans up."""

import os
import re
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.main import app
from tests import harness
from tests.harness import BACKEND_DIR, START_DB_HINT, TABLES
from tests.helpers import insert_child, insert_session_with_words, insert_word


def count(connection, table):
    return connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def assert_all_tables_empty(connection):
    assert {table: count(connection, table) for table in TABLES} == dict.fromkeys(TABLES, 0)


@pytest.fixture
def stand_in_routes():
    """Register throwaway routes on the real app (no profile route exists yet) and remove them afterwards."""
    before = list(app.router.routes)

    @app.post("/__harness/children")
    def create_child(session: Session = Depends(get_session)):
        child_id = insert_child(session)
        session.commit()
        return {"id": str(child_id)}

    @app.get("/__harness/children/count")
    def count_children(session: Session = Depends(get_session)):
        return {"count": count(session, "children")}

    @app.get("/__harness/db")
    def current_database(session: Session = Depends(get_session)):
        return {"name": session.execute(text("SELECT current_database()")).scalar_one()}

    yield
    app.router.routes[:] = before
    app.openapi_schema = None


# --- clean state between tests (test_a/test_b are the two proof tests: both insert and commit one child) ---

def test_a(clean_db):
    with clean_db.begin() as connection:
        insert_child(connection)
    with clean_db.connect() as connection:
        assert count(connection, "children") == 1


def test_b(clean_db):
    with clean_db.begin() as connection:
        insert_child(connection)
    with clean_db.connect() as connection:
        assert count(connection, "children") == 1


def test_all_seven_tables_are_empty_at_start(clean_db):
    with clean_db.connect() as connection:
        assert_all_tables_empty(connection)


def test_alembic_version_is_kept_between_tests(clean_db):
    with clean_db.connect() as connection:
        assert count(connection, "alembic_version") == 1


def test_route_commit_leaves_a_row(client, stand_in_routes):
    assert client.post("/__harness/children").status_code == 200
    assert client.get("/__harness/children/count").json() == {"count": 1}


def test_row_committed_by_previous_route_test_is_gone(clean_db):
    with clean_db.connect() as connection:
        assert_all_tables_empty(connection)


def test_cleanup_removes_rows_in_every_table(clean_db):
    with clean_db.begin() as connection:
        insert_session_with_words(connection)
        assert count(connection, "sessions") == 1
        assert count(connection, "session_words") == 2


def test_after_multi_table_commit_all_tables_are_empty(clean_db):
    with clean_db.connect() as connection:
        assert_all_tables_empty(connection)


# --- client wiring ---

def test_client_session_uses_the_test_database_not_the_development_one(client, db_session, stand_in_routes):
    name = client.get("/__harness/db").json()["name"]
    dev_name = get_settings().database_url.rsplit("/", 1)[1].split("?")[0]
    assert name.startswith("wordwise_test_")
    assert name != dev_name
    assert db_session.execute(text("SELECT current_database()")).scalar_one() == name


def test_row_the_test_commits_is_visible_to_a_route(client, db_session, stand_in_routes):
    insert_child(db_session)
    db_session.commit()
    assert client.get("/__harness/children/count").json() == {"count": 1}


def test_row_a_route_commits_is_visible_to_the_test(client, db_session, stand_in_routes):
    client.post("/__harness/children")
    assert count(db_session, "children") == 1


def test_client_overrides_get_session(client):
    assert get_session in app.dependency_overrides


def test_no_dependency_override_leaks_into_the_next_test():
    assert app.dependency_overrides == {}


def test_stand_in_routes_are_removed_after_each_test():
    assert not [route for route in app.router.routes if getattr(route, "path", "").startswith("/__harness")]


# --- helpers ---

def test_helpers_insert_valid_rows_with_overrides(db_session):
    child_id = insert_child(db_session, nickname="Zed", grade="K")
    word_id = insert_word(db_session, word="kiwi")
    session_id = insert_session_with_words(db_session, child_id=child_id, word_ids=[word_id], mode="review")
    db_session.commit()
    assert tuple(db_session.execute(text("SELECT nickname, grade FROM children WHERE id = :i"), {"i": child_id}).one()) == ("Zed", "K")
    assert db_session.execute(text("SELECT word FROM words WHERE id = :i"), {"i": word_id}).scalar_one() == "kiwi"
    assert db_session.execute(text("SELECT mode FROM sessions WHERE id = :i"), {"i": session_id}).scalar_one() == "review"
    assert count(db_session, "session_words") == 1


def test_session_helper_defaults_create_its_child_and_words(db_session):
    insert_session_with_words(db_session, word_count=3)
    db_session.commit()
    assert (count(db_session, "children"), count(db_session, "words"), count(db_session, "session_words")) == (1, 3, 3)


# --- failure behaviour ---

def run_pytest(*args, database_url=None):
    env = {**os.environ}
    if database_url:
        env["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True,
    )


def test_unreachable_database_fails_harness_tests_quickly_and_not_the_others():
    closed_port = "postgresql+psycopg://wordwise:change-me@localhost:5999/wordwise"
    started = time.monotonic()
    result = run_pytest(
        "tests/test_harness.py::test_a", "tests/test_harness.py::test_b",
        "tests/test_health.py", "tests/test_config.py", "tests/test_cors.py",
        database_url=closed_port,
    )
    elapsed = time.monotonic() - started
    summary = result.stdout.strip().splitlines()[-1]
    assert result.returncode != 0
    assert START_DB_HINT in result.stdout
    assert re.search(r"\b2 errors\b", summary)  # a failing fixture is reported as an error: not skipped, not passed
    assert "failed" not in summary
    assert re.search(r"\b\d+ passed\b", summary)  # health, config and cors need no database
    assert elapsed < 30


def database_exists(engine, name):
    with engine.connect() as connection:
        return bool(connection.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}).all())


def test_migration_failure_fails_with_alembic_stderr_and_drops_the_database(monkeypatch, clean_db):
    seen = []

    def failing_alembic(url, *args):
        seen.append(url.rsplit("/", 1)[1])
        return SimpleNamespace(returncode=1, stderr="boom: relation exploded")

    monkeypatch.setattr(harness, "run_alembic", failing_alembic)
    with pytest.raises(pytest.fail.Exception, match="boom: relation exploded"):
        with harness.migrated_database():
            pytest.fail("body must not run")
    assert not database_exists(clean_db, seen[0])


def test_database_is_dropped_when_the_body_raises(clean_db):
    name = None
    with pytest.raises(RuntimeError):
        with harness.migrated_database() as url:
            name = url.rsplit("/", 1)[1]
            assert database_exists(clean_db, name)
            raise RuntimeError("test failed")
    assert not database_exists(clean_db, name)
