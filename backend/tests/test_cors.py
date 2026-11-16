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


def test_preflight_allows_the_profile_write_methods_and_json_content_type():
    app = create_app(load_settings(_env_file=None, database_url=GOOD_URL, cors_origins="http://localhost:8080"))
    for method in ("POST", "PUT", "DELETE"):
        response = TestClient(app).options(
            "/api/v1/profiles",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200, method
        assert method in response.headers["access-control-allow-methods"]
