from fastapi.testclient import TestClient

from app.main import app


def test_reports_routes_are_registered_and_protected():
    client = TestClient(app)

    firm_response = client.get("/api/v1/reports/firm-client-reports")
    global_response = client.get("/api/v1/reports/global-client-reports")

    assert firm_response.status_code == 401
    assert global_response.status_code == 401
