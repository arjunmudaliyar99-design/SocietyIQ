from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_only_built_domains_are_mounted() -> None:
    # Stubs exist for every domain; only those whose milestone is built are exposed.
    prefixes = {p.split("/")[3] for p in app.openapi()["paths"]}
    assert prefixes == {"health", "me", "societies"}
