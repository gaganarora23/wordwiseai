from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "broken-on-purpose"}


def test_post_health_returns_405():
    assert client.post("/api/v1/health").status_code == 405


def test_unknown_api_route_returns_404():
    assert client.get("/api/v1/nope").status_code == 404


def test_health_without_prefix_returns_404():
    assert client.get("/health").status_code == 404


def test_openapi_is_3_1_and_includes_health_path():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["openapi"].startswith("3.1.")
    schema = spec["paths"]["/api/v1/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/HealthResponse")


def test_docs_page_loads():
    assert client.get("/docs").status_code == 200
