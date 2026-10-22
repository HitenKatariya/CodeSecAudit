"""Test webhook signature verification and fail-closed security."""

import hashlib
import hmac
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.core.config import get_settings
from app.security.signatures import verify_github_signature

app_for_test = FastAPI()


@app_for_test.post("/test-webhook")
async def dummy_webhook(request: Request):
    await verify_github_signature(request)
    return {"status": "verified"}


client = TestClient(app_for_test)


@pytest.fixture(autouse=True)
def configure_test_secret(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "github_webhook_secret", "test-secret-123")


def test_missing_signature_fails_closed():
    resp = client.post("/test-webhook", json={"test": "payload"})
    assert resp.status_code == 401
    assert "Missing X-Hub-Signature-256" in resp.json()["detail"]


def test_invalid_signature_fails_closed():
    resp = client.post(
        "/test-webhook",
        json={"test": "payload"},
        headers={"X-Hub-Signature-256": "sha256=invalidhexsignature000000000000000000000000"},
    )
    assert resp.status_code == 401
    assert "Invalid webhook signature" in resp.json()["detail"]


def test_valid_signature_succeeds():
    secret = "test-secret-123"
    payload = b'{"action":"opened"}'
    valid_sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    resp = client.post(
        "/test-webhook",
        content=payload,
        headers={"X-Hub-Signature-256": valid_sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "verified"}
