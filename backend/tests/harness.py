"""Plumbing of the integration test harness: one migrated throwaway database per pytest run.

Plain functions only; the fixtures that use them live in ``conftest.py``. Nothing here
touches the database named in ``DATABASE_URL`` except to connect to it and issue
``CREATE DATABASE`` / ``DROP DATABASE`` for the ``wordwise_test_*`` database it owns.
"""

import os
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
START_DB_HINT = "docker compose up -d --wait db"
TABLES = ("children", "words", "sessions", "session_words", "answers", "quiz_results", "word_mastery")


def run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess:
    """Run the alembic CLI from backend/ against ``database_url`` (real env wins over .env)."""
    env = {**os.environ, "DATABASE_URL": database_url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True,
    )


@contextmanager
def migrated_database():
    """Create a new ``wordwise_test_<random>`` database next to the configured one, migrate it to head, yield its URL, drop it.

    The database is dropped on every exit path (test failures, migration failure, interrupts).
    """
    base = make_url(get_settings().database_url)
    name = f"wordwise_test_{uuid.uuid4().hex[:12]}"
    assert name != base.database  # never the development database
    admin = create_engine(base, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
    try:
        try:
            with admin.connect() as connection:
                connection.execute(text(f'CREATE DATABASE "{name}"'))
        except OperationalError:
            pytest.fail(f"PostgreSQL is not reachable. Start it with: {START_DB_HINT}", pytrace=False)
        try:
            url = base.set(database=name).render_as_string(hide_password=False)
            result = run_alembic(url, "upgrade", "head")
            if result.returncode != 0:
                pytest.fail(f"alembic upgrade head failed on {name}:\n{result.stderr}", pytrace=False)
            yield url
        finally:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        admin.dispose()


def truncate_all(engine) -> None:
    """Empty the seven application tables (``alembic_version`` is left alone)."""
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
