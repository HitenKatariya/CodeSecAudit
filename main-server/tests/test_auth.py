"""Tests for authentication and session endpoints."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_auth_me_unauthenticated():
    resp = client.get("/v1/auth/me")
    assert resp.status_code == 401
    assert "Not authenticated" in resp.text


def test_auth_login_validation():
    resp = client.post("/v1/auth/login", json={"username": ""})
    assert resp.status_code == 400


def test_auth_logout_empty():
    resp = client.post("/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Logged out"}
