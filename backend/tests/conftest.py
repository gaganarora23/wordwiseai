import os
from pathlib import Path

# The app needs a database URL at import time (no database has to be running).
# Without a repo-root .env, fall back to the .env.example value.
if not (Path(__file__).resolve().parents[2] / ".env").exists():
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://wordwise:change-me@localhost:5432/wordwise",
    )

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.main import app
from tests.harness import START_DB_HINT, migrated_database, run_alembic, truncate_all  # noqa: F401  (run_alembic is imported from here by test_migrations)


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


# --- Integration harness: one migrated database per run, truncated after every test ---


@pytest.fixture(scope="session")
def harness_db_url():
    """URL of a new ``wordwise_test_*`` database, migrated once per run and dropped at the end of it."""
    with migrated_database() as url:
        yield url


@pytest.fixture(scope="session")
def harness_engine(harness_db_url):
    engine = create_engine(harness_db_url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_db(harness_engine):
    """The migrated test database (an Engine), emptied of all rows after the test, committed or not."""
    truncate_all(harness_engine)  # also covers a previous test that skipped its teardown
    try:
        yield harness_engine
    finally:
        truncate_all(harness_engine)


@pytest.fixture
def db_session(clean_db):
    """A Session on the test database for the test's own inserts and queries; commit to make rows visible to routes."""
    session = Session(clean_db)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(clean_db):
    """TestClient for the real app whose ``get_session`` yields sessions bound to the test database."""

    def override_get_session():
        session = Session(clean_db)
        try:
            yield session
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
