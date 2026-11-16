"""Alembic upgrade/downgrade behaviour, always on a throwaway database."""

from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic


def tables(url):
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def ok(url, *args):
    result = run_alembic(url, *args)
    assert result.returncode == 0, result.stderr
    return result


def schema_snapshot(url):
    engine = create_engine(url)
    try:
        with engine.connect() as c:
            cols = c.execute(text(
                "SELECT table_name, column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_schema='public' ORDER BY 1, 2")).all()
            checks = c.execute(text(
                "SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) "
                "FROM pg_constraint WHERE connamespace='public'::regnamespace AND conrelid::regclass::text <> 'alembic_version' ORDER BY 1, 2")).all()
        return cols, checks
    finally:
        engine.dispose()


def test_upgrade_creates_tables_and_is_idempotent(throwaway_db_url):
    ok(throwaway_db_url, "upgrade", "head")
    assert tables(throwaway_db_url) == {"alembic_version", "children", "words"}
    before = schema_snapshot(throwaway_db_url)
    ok(throwaway_db_url, "upgrade", "head")
    assert schema_snapshot(throwaway_db_url) == before


def test_downgrade_base_removes_tables_and_round_trip_restores_same_schema(throwaway_db_url):
    ok(throwaway_db_url, "upgrade", "head")
    first = schema_snapshot(throwaway_db_url)
    ok(throwaway_db_url, "downgrade", "base")
    assert tables(throwaway_db_url) == {"alembic_version"}
    engine = create_engine(throwaway_db_url)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM pg_constraint WHERE connamespace='public'::regnamespace AND conrelid::regclass::text <> 'alembic_version'")).scalar_one() == 0
    engine.dispose()
    ok(throwaway_db_url, "upgrade", "head")
    assert tables(throwaway_db_url) == {"alembic_version", "children", "words"}
    assert schema_snapshot(throwaway_db_url) == first


def test_models_and_migration_agree(throwaway_db_url):
    ok(throwaway_db_url, "upgrade", "head")
    result = ok(throwaway_db_url, "check")
    assert "No new upgrade operations detected" in result.stdout + result.stderr


def test_there_is_a_single_linear_head(throwaway_db_url):
    ok(throwaway_db_url, "upgrade", "head")
    heads = ok(throwaway_db_url, "heads").stdout.strip().splitlines()
    assert len(heads) == 1
    assert "(head)" in ok(throwaway_db_url, "current").stdout


def test_invalid_database_url_fails_with_one_line_and_no_password(throwaway_db_url):
    result = run_alembic("postgresql://u:secretpw@localhost/x", "upgrade", "head")
    assert result.returncode != 0
    assert "Configuration error: DATABASE_URL must be set" in result.stderr
    assert "secretpw" not in result.stderr + result.stdout
    assert "Traceback" not in result.stderr
