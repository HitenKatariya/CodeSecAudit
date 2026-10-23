"""Tests for authentication and session endpoints."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_auth_me_unauthenticated():
    resp = client.get("/v1/auth/me")
    assert resp.status_code == 401
    assert "Not authenticated" in resp.text


def test_auth_delete_account_unauthenticated():
    resp = client.delete("/v1/auth/account")
    assert resp.status_code == 401
    assert "Not authenticated" in resp.text


def test_auth_login_validation():
    resp = client.post("/v1/auth/login", json={"username": ""})
    assert resp.status_code == 400


def test_auth_logout_empty():
    resp = client.post("/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Logged out"}


def test_github_callback_app_install_success(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    import app.api.auth as auth_module
    from app.db.session import get_db

    mock_user_data = {
        "id": "999888777",
        "login": "testinstaller",
        "avatar_url": "https://avatars.githubusercontent.com/u/999888777",
    }
    monkeypatch.setattr(
        auth_module,
        "exchange_github_app_code",
        AsyncMock(return_value=(mock_user_data, "installer@example.com")),
    )
    monkeypatch.setattr(
        auth_module,
        "sync_installation_repositories",
        AsyncMock(return_value=[
            {"id": "12345", "name": "sample-repo", "full_name": "testinstaller/sample-repo", "private": False}
        ]),
    )

    async def mock_create_session(resp, uid, oid):
        resp.set_cookie("codesec_session", "mock_session_id")
        return "mock_session_id"

    monkeypatch.setattr(auth_module, "create_user_session", mock_create_session)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        # Calling callback without 'state' parameter (as GitHub App install does)
        resp = client.get(
            "/v1/auth/github/callback?code=mock_code&installation_id=174566248&setup_action=install",
            follow_redirects=False,
        )

        # Must NOT return 422 Unprocessable Entity
        assert resp.status_code == 302
        assert "/dashboard?installed=true" in resp.headers["location"]
        # Session cookie must be set
        assert "codesec_session" in resp.headers.get("set-cookie", "")
    finally:
        app.dependency_overrides.pop(get_db, None)



def test_github_callback_no_auth_redirects_login():
    resp = client.get("/v1/auth/github/callback", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login?error=oauth_failed" in resp.headers["location"]

