from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_health_route_returns_service_name():
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": settings.app_name}


def test_healthz_validates_dependencies():
    client = TestClient(app)
    response = client.get("/api/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": settings.app_name,
        "database": "ok",
    }
