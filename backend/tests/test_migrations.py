"""Alembic upgrade/downgrade behaviour, always on a throwaway database."""

from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic


ALL_TABLES = {
    "alembic_version", "children", "words", "sessions", "session_words", "answers", "quiz_results", "word_mastery",
}
TABLES_AT_0002 = ALL_TABLES - {"quiz_results", "word_mastery"}
BASE_TABLES = {"alembic_version", "children", "words"}


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
            indexes = c.execute(text(
                "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname='public' "
                "AND tablename <> 'alembic_version' ORDER BY 1, 2")).all()
        return cols, checks, indexes
    finally:
        engine.dispose()


def test_upgrade_creates_tables_and_is_idempotent(throwaway_db_url):
    ok(throwaway_db_url, "upgrade", "head")
    assert tables(throwaway_db_url) == ALL_TABLES
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
    assert tables(throwaway_db_url) == ALL_TABLES
    assert schema_snapshot(throwaway_db_url) == first


def test_downgrade_0002_removes_only_results_and_mastery_and_keeps_rows(throwaway_db_url):
    ok(throwaway_db_url, "upgrade", "head")
    child_id = "00000000-0000-0000-0000-000000000001"
    session_id = "00000000-0000-0000-0000-000000000002"
    engine = create_engine(throwaway_db_url)
    with engine.begin() as c:
        c.execute(text("INSERT INTO children (id, nickname, grade, daily_goal) VALUES (:i, 'Sam', '3', 5)"), {"i": child_id})
        c.execute(text(
            "INSERT INTO words (id, word, grade, definition, example, syllables, content_version, "
            "option_1, option_2, option_3, option_4, correct_option, explanation) "
            "VALUES (:i, 'w', '1', 'd', 'e', 's', 'v1', 'a', 'b', 'c', 'd', 1, 'x')"), {"i": child_id})
        c.execute(text(
            "INSERT INTO sessions (id, child_id, mode, phase, status, current_position) "
            "VALUES (:s, :c, 'daily', 'learning', 'in_progress', 0)"), {"s": session_id, "c": child_id})
        c.execute(text("INSERT INTO session_words (session_id, word_id, position) VALUES (:s, :w, 0)"), {"s": session_id, "w": child_id})
        c.execute(text("INSERT INTO answers (session_id, word_id, selected_option, is_correct, hint_used) VALUES (:s, :w, 1, true, false)"),
                  {"s": session_id, "w": child_id})
        c.execute(text(
            "INSERT INTO quiz_results (session_id, score, correct_count, incorrect_count) VALUES (:s, 1, 1, 0)"), {"s": session_id})
        c.execute(text("INSERT INTO word_mastery (child_id, word_id) VALUES (:c, :w)"), {"c": child_id, "w": child_id})
    engine.dispose()
    ok(throwaway_db_url, "downgrade", "0002")
    assert tables(throwaway_db_url) == TABLES_AT_0002
    assert "0002" in ok(throwaway_db_url, "current").stdout
    engine = create_engine(throwaway_db_url)
    with engine.connect() as c:
        for table in ("children", "words", "sessions", "session_words", "answers"):
            assert c.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 1, table
    engine.dispose()


def test_downgrade_0002_then_base_then_upgrade_restores_same_schema(throwaway_db_url):
    ok(throwaway_db_url, "upgrade", "head")
    first = schema_snapshot(throwaway_db_url)
    ok(throwaway_db_url, "downgrade", "0002")
    ok(throwaway_db_url, "downgrade", "base")
    assert tables(throwaway_db_url) == {"alembic_version"}
    ok(throwaway_db_url, "upgrade", "head")
    assert tables(throwaway_db_url) == ALL_TABLES
    assert schema_snapshot(throwaway_db_url) == first


def test_downgrade_0001_removes_only_the_session_tables_and_keeps_rows(throwaway_db_url):
    ok(throwaway_db_url, "upgrade", "head")
    child_id = "00000000-0000-0000-0000-000000000001"
    engine = create_engine(throwaway_db_url)
    with engine.begin() as c:
        c.execute(text("INSERT INTO children (id, nickname, grade, daily_goal) VALUES (:i, 'Sam', '3', 5)"), {"i": child_id})
        c.execute(text(
            "INSERT INTO words (id, word, grade, definition, example, syllables, content_version, "
            "option_1, option_2, option_3, option_4, correct_option, explanation) "
            "VALUES (:i, 'w', '1', 'd', 'e', 's', 'v1', 'a', 'b', 'c', 'd', 1, 'x')"), {"i": child_id})
    engine.dispose()
    ok(throwaway_db_url, "downgrade", "0001")
    assert tables(throwaway_db_url) == BASE_TABLES
    assert "0001" in ok(throwaway_db_url, "current").stdout
    engine = create_engine(throwaway_db_url)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM children")).scalar_one() == 1
        assert c.execute(text("SELECT count(*) FROM words")).scalar_one() == 1
    engine.dispose()


def test_downgrade_0001_then_base_then_upgrade_restores_same_schema(throwaway_db_url):
    ok(throwaway_db_url, "upgrade", "head")
    first = schema_snapshot(throwaway_db_url)
    ok(throwaway_db_url, "downgrade", "0001")
    ok(throwaway_db_url, "downgrade", "base")
    assert tables(throwaway_db_url) == {"alembic_version"}
    ok(throwaway_db_url, "upgrade", "head")
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
    result = run_alembic("mysql://u:secretpw@localhost/x", "upgrade", "head")
    assert result.returncode != 0
    assert "Configuration error: DATABASE_URL must be set" in result.stderr
    assert "secretpw" not in result.stderr + result.stdout
    assert "Traceback" not in result.stderr
