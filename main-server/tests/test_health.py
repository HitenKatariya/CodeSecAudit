"""Test health and version endpoints on main-server."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_live():
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_version():
    resp = client.get("/version")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "main-server"
    assert "version" in data
