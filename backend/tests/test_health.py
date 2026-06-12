import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_ok_status():
    response = client.get("/api/health")
    data = response.json()
    assert data["status"] == "ok"


def test_health_returns_version():
    response = client.get("/api/health")
    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


def test_health_cors_header_present():
    """CORS preflight — OPTIONS should not 405 for the allowed origin."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5177",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI CORS middleware returns 200 for preflight
    assert response.status_code == 200
