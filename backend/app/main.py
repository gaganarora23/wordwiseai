from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, profiles, words
from app.config import ConfigError, Settings, get_settings
from app.db import get_engine


def create_app(settings: Settings) -> FastAPI:
    application = FastAPI(title="WordWise API")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )
    application.include_router(health.router, prefix="/api/v1")
    application.include_router(profiles.router, prefix="/api/v1")
    application.include_router(words.router, prefix="/api/v1")
    return application


try:
    _settings = get_settings()
    get_engine()  # builds the engine; does not connect
except ConfigError as exc:
    # One readable line instead of a traceback.
    raise SystemExit(f"Configuration error: {exc}") from None

app = create_app(_settings)
