import time

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_engine, get_session
from app.main import app as main_app

START_DB = "docker compose up -d --wait db"


@pytest.fixture
def fresh_engine(monkeypatch):
    """Rebuild settings and engine around the test's DATABASE_URL, restore afterwards."""

    def configure(url=None):
        if url is not None:
            monkeypatch.setenv("DATABASE_URL", url)
        get_settings.cache_clear()
        get_engine.cache_clear()
        return get_engine()

    yield configure
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture
def db_engine(fresh_engine):
    engine = fresh_engine()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        pytest.fail(f"PostgreSQL is not reachable. Start it with: {START_DB}", pytrace=False)
    return engine


def make_app():
    app = FastAPI()
    seen: list[Session] = []

    @app.get("/one")
    def one(session: Session = Depends(get_session)):
        seen.append(session)
        return {"same": True}

    @app.get("/twice")
    def twice(a: Session = Depends(get_session), b: Session = Depends(get_session)):
        return {"same": a is b}

    return app, seen


def test_engine_is_sync_psycopg_with_pre_ping_and_is_cached(fresh_engine):
    engine = fresh_engine()
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"
    assert engine.pool._pre_ping is True
    assert get_engine() is engine


def test_two_requests_get_different_sessions():
    app, seen = make_app()
    client = TestClient(app)
    client.get("/one")
    client.get("/one")
    assert seen[0] is not seen[1]


def test_dependency_used_twice_in_one_request_gets_same_session():
    app, _ = make_app()
    assert TestClient(app).get("/twice").json() == {"same": True}


def test_dependency_override_is_honoured():
    app, _ = make_app()
    sentinel = object()
    app.dependency_overrides[get_session] = lambda: sentinel

    @app.get("/who")
    def who(session=Depends(get_session)):
        return {"is_sentinel": session is sentinel}

    assert TestClient(app).get("/who").json() == {"is_sentinel": True}


def test_health_is_ok_with_database_at_closed_port(fresh_engine):
    # Importing/using the app never connects; the already-built app must answer.
    fresh_engine("postgresql+psycopg://u:pw@127.0.0.1:1/db")
    response = TestClient(main_app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unreachable_database_raises_operational_error_quickly(fresh_engine):
    fresh_engine("postgresql+psycopg://u:pw@127.0.0.1:1/db")
    app, _ = make_app()

    @app.get("/q")
    def q(session: Session = Depends(get_session)):
        return session.execute(text("SELECT 1")).scalar_one()

    started = time.monotonic()
    with pytest.raises(OperationalError):
        TestClient(app).get("/q")
    assert time.monotonic() - started < 10


def test_select_1_through_dependency_returns_1(db_engine):
    app = FastAPI()

    @app.get("/q")
    def q(session: Session = Depends(get_session)):
        return session.execute(text("SELECT 1")).scalar_one()

    assert TestClient(app).get("/q").json() == 1


def test_session_is_closed_after_success_and_after_error(db_engine):
    app = FastAPI()
    seen: list[Session] = []

    @app.get("/ok")
    def ok(session: Session = Depends(get_session)):
        seen.append(session)
        session.execute(text("SELECT 1"))
        return {}

    @app.get("/boom")
    def boom(session: Session = Depends(get_session)):
        seen.append(session)
        session.execute(text("SELECT 1"))
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/ok").status_code == 200
    assert client.get("/boom").status_code == 500
    for session in seen:
        assert not session.in_transaction()
    assert db_engine.pool.checkedout() == 0


def test_unhandled_error_rolls_back_uncommitted_changes(db_engine):
    with db_engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS session_rollback_probe"))
        connection.execute(text("CREATE TABLE session_rollback_probe (x int)"))
    try:
        app = FastAPI()

        @app.get("/boom")
        def boom(session: Session = Depends(get_session)):
            session.execute(text("INSERT INTO session_rollback_probe VALUES (1)"))
            raise RuntimeError("boom")

        @app.get("/commit-not-called")
        def no_commit(session: Session = Depends(get_session)):
            session.execute(text("INSERT INTO session_rollback_probe VALUES (2)"))
            return {}

        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/boom").status_code == 500
        assert client.get("/commit-not-called").status_code == 200
        with db_engine.connect() as connection:
            count = connection.execute(text("SELECT count(*) FROM session_rollback_probe")).scalar_one()
        assert count == 0  # error rolled back, and the dependency never commits on its own
    finally:
        with db_engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS session_rollback_probe"))
