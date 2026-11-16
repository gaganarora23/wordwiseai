"""Application settings read from the environment and the repo-root ``.env``.

Real environment variables win over ``.env``. Settings are built once per
process through :func:`get_settings`.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/app/config.py -> repo root is two levels above ``backend/``.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

DATABASE_URL_PREFIX = "postgresql+psycopg://"

# Connection settings, also documented in the README Database section.
DB_CONNECT_TIMEOUT_SECONDS = 5
DB_POOL_PRE_PING = True


class ConfigError(Exception):
    """Settings are missing or invalid. The message is safe to print (no secrets)."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str = ""
    cors_origins: Annotated[list[str], NoDecode] = []

    @field_validator("database_url")
    @classmethod
    def _check_database_url(cls, value: str) -> str:
        # Fixed message on purpose: pydantic would otherwise echo the value (and password).
        if not value.startswith(DATABASE_URL_PREFIX) or value == DATABASE_URL_PREFIX:
            raise ValueError(
                f"DATABASE_URL must be set and start with '{DATABASE_URL_PREFIX}'"
            )
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


def load_settings(**kwargs: object) -> Settings:
    """Build settings, turning validation errors into a one-line :class:`ConfigError`."""
    try:
        return Settings(**kwargs)
    except ValidationError as exc:
        names = {"database_url": "DATABASE_URL", "cors_origins": "CORS_ORIGINS"}
        problems = []
        for err in exc.errors():
            field = str(err["loc"][0]) if err["loc"] else ""
            if field == "database_url":
                problems.append(
                    f"DATABASE_URL must be set and start with '{DATABASE_URL_PREFIX}'"
                )
            else:
                problems.append(f"{names.get(field, field)} is invalid")
        raise ConfigError("; ".join(problems)) from None


@lru_cache
def get_settings() -> Settings:
    return load_settings()
