import os
from pathlib import Path

# The app needs a database URL at import time (no database has to be running).
# Without a repo-root .env, fall back to the .env.example value.
if not (Path(__file__).resolve().parents[2] / ".env").exists():
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://wordwise:change-me@localhost:5432/wordwise",
    )

import subprocess
import sys
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
START_DB_HINT = "docker compose up -d --wait db"


def run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess:
    """Run the alembic CLI from backend/ against ``database_url`` (real env wins over .env)."""
    env = {**os.environ, "DATABASE_URL": database_url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True,
    )


@pytest.fixture
def throwaway_db_url():
    """Create an empty database next to the configured one and drop it afterwards."""
    base = make_url(get_settings().database_url)
    name = f"wordwise_test_{uuid.uuid4().hex[:12]}"
    admin = create_engine(base, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    except OperationalError:
        admin.dispose()
        pytest.fail(f"PostgreSQL is not reachable. Start it with: {START_DB_HINT}", pytrace=False)
    try:
        yield base.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def migrated_connection(throwaway_db_url):
    """A connection to a freshly migrated throwaway database, inside a transaction rolled back after the test."""
    result = run_alembic(throwaway_db_url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    engine = create_engine(throwaway_db_url)
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()
