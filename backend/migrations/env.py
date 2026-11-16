"""Alembic environment. The database URL comes from ``app.config`` (never from alembic.ini)."""

from logging.config import fileConfig

from alembic import context

from app.config import ConfigError, get_settings
from app.db import get_engine
from app.models import Base  # noqa: F401  (importing app.models registers Child and Word)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

try:
    database_url = get_settings().database_url
except ConfigError as exc:
    # One readable line, no traceback (and never the password).
    raise SystemExit(f"Configuration error: {exc}") from None


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = get_engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
