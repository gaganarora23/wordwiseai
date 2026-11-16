from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app

GOOD_URL = "postgresql+psycopg://u:pw@localhost:5432/db"


def preflight(cors_origins: str, origin: str):
    app = create_app(load_settings(_env_file=None, database_url=GOOD_URL, cors_origins=cors_origins))
    return TestClient(app).options(
        "/api/v1/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )


def test_preflight_from_listed_origin_is_allowed():
    response = preflight("http://localhost:8080", "http://localhost:8080")
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"


def test_preflight_from_unlisted_origin_is_not_allowed():
    response = preflight("http://localhost:8080", "http://evil.example")
    assert "access-control-allow-origin" not in response.headers


def test_no_origins_configured_allows_none():
    response = preflight("", "http://localhost:8080")
    assert "access-control-allow-origin" not in response.headers
