"""Synchronous SQLAlchemy engine and the per-request session dependency.

The engine is created once per process and does not connect until first use,
so the app starts without a database. Connection settings (see ``app.config``):
``connect_timeout`` is 5 seconds and ``pool_pre_ping`` is on.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import DB_CONNECT_TIMEOUT_SECONDS, DB_POOL_PRE_PING, get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        connect_args={"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS},
        pool_pre_ping=DB_POOL_PRE_PING,
    )


def get_session() -> Iterator[Session]:
    """Yield one session per request. Never commits; the caller (services) does."""
    session = Session(get_engine())
    try:
        yield session
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
