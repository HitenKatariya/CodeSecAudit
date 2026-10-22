"""Unit tests for RAG Server API endpoints."""

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
    assert data["service"] == "rag-server"
    assert "version" in data


def test_search_unauthorized():
    resp = client.post("/v1/search", json={"query": "sql injection", "top_k": 3})
    assert resp.status_code == 401
    assert "Missing required internal service token" in resp.json()["detail"]


def test_search_invalid_token():
    resp = client.post(
        "/v1/search",
        json={"query": "sql injection", "top_k": 3},
        headers={"X-Internal-RAG-Token": "wrong-token"},
    )
    assert resp.status_code == 401
    assert "Invalid internal service token" in resp.json()["detail"]
