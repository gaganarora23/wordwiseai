import subprocess
import sys
from pathlib import Path

import pytest

from app.config import ENV_FILE, ConfigError, get_settings, load_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
GOOD_URL = "postgresql+psycopg://u:pw@localhost:5432/db"


def settings(**env):
    return load_settings(_env_file=None, **env)


def test_cors_origins_are_split_trimmed_and_empty_dropped(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", GOOD_URL)
    monkeypatch.setenv("CORS_ORIGINS", "http://a, http://b,")
    assert settings().cors_origins == ["http://a", "http://b"]


@pytest.mark.parametrize("value", [None, ""])
def test_cors_origins_unset_or_empty_gives_empty_list(monkeypatch, value):
    monkeypatch.setenv("DATABASE_URL", GOOD_URL)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    if value is not None:
        monkeypatch.setenv("CORS_ORIGINS", value)
    assert settings().cors_origins == []


def test_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", GOOD_URL)
    assert settings().database_url == GOOD_URL


def test_get_settings_returns_the_same_object():
    assert get_settings() is get_settings()


def test_env_file_is_at_repo_root():
    assert ENV_FILE == BACKEND_DIR.parent / ".env"


def test_env_file_is_read_and_real_env_wins(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+psycopg://f:f@h:1/f\nCORS_ORIGINS=http://file\n"
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CORS_ORIGINS", "http://env")
    loaded = load_settings(_env_file=env_file)
    assert loaded.database_url == "postgresql+psycopg://f:f@h:1/f"
    assert loaded.cors_origins == ["http://env"]


def test_missing_database_url_error_names_it(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        settings()


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "sqlite:///x.db",
        "postgresql://u:s3cret-pw@localhost/db",
    ],
)
def test_bad_database_url_error_is_readable_and_hides_password(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ConfigError) as info:
        settings()
    message = str(info.value)
    assert "postgresql+psycopg://" in message
    assert "DATABASE_URL" in message
    assert "s3cret-pw" not in message
    assert "\n" not in message


def run_import_app(env_overrides):
    env = {"PATH": "/usr/bin:/bin", **env_overrides}
    return subprocess.run(
        [sys.executable, "-I", "-c", "import sys; sys.path.insert(0, '.'); import app.main"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("url", ["", "not a url", "sqlite:///x.db", "postgresql://u:s3cret-pw@h/db"])
def test_startup_with_bad_database_url_exits_with_one_line(url):
    result = run_import_app({"DATABASE_URL": url})
    assert result.returncode != 0
    assert result.stderr.strip().count("\n") == 0
    assert "DATABASE_URL" in result.stderr
    assert "Traceback" not in result.stderr
    assert "s3cret-pw" not in result.stderr


@pytest.mark.skipif(ENV_FILE.exists(), reason="a repo-root .env may supply DATABASE_URL")
def test_startup_with_database_url_unset_exits_with_one_line():
    result = run_import_app({})
    assert result.returncode != 0
    assert result.stderr.strip().count("\n") == 0
    assert "DATABASE_URL" in result.stderr
    assert "Traceback" not in result.stderr
