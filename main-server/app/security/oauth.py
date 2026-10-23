"""GitHub OAuth 2.0 with PKCE and secure CSRF state verification."""

import base64
import hashlib
import json
import secrets
from urllib.parse import urlencode
import httpx
from app.core.config import get_settings
from app.core.redis import get_redis_service


def _generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


async def create_oauth_authorization_url(redirect_uri: str) -> str:
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    verifier, challenge = _generate_pkce_pair()

    redis_service = get_redis_service(settings.redis_url)
    client = await redis_service.get_async()
    payload = json.dumps({"verifier": verifier, "redirect_uri": redirect_uri})
    await client.setex(f"oauth_state:{state}", 600, payload)

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "read:user user:email",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


async def verify_oauth_callback(code: str, state: str) -> tuple[dict, str]:
    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    client = await redis_service.get_async()

    raw_state_data = await client.get(f"oauth_state:{state}")
    if not raw_state_data:
        raise ValueError("Invalid or expired OAuth state")
    await client.delete(f"oauth_state:{state}")

    state_data = json.loads(raw_state_data)
    verifier = state_data["verifier"]
    redirect_uri = state_data["redirect_uri"]

    async with httpx.AsyncClient(timeout=15.0) as http:
        token_resp = await http.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError(f"OAuth exchange failed: {token_data.get('error_description')}")

        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github.v3+json"}
        user_resp = await http.get("https://api.github.com/user", headers=headers)
        user_data = user_resp.json()

        email_resp = await http.get("https://api.github.com/user/emails", headers=headers)
        emails = email_resp.json() if email_resp.is_success else []

        primary_email = user_data.get("email") or ""
        for em in emails:
            if em.get("primary") and em.get("verified"):
                primary_email = em.get("email")
                break

        return user_data, primary_email


async def exchange_github_app_code(code: str) -> tuple[dict, str]:
    """Exchange authorization code obtained during GitHub App installation.

    When a GitHub App is configured with 'Request user authorization (OAuth) during installation',
    GitHub redirects to the setup/callback URL with ?code=...&installation_id=...&setup_action=install.
    In this installation flow, no PKCE challenge was initiated by the client, so credentials
    are exchanged directly using client_id + client_secret + code.
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15.0) as http:
        token_resp = await http.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            err = token_data.get("error_description") or token_data.get("error") or "no access token"
            raise ValueError(f"GitHub App code exchange failed: {err}")

        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github.v3+json"}
        user_resp = await http.get("https://api.github.com/user", headers=headers)
        user_data = user_resp.json()

        email_resp = await http.get("https://api.github.com/user/emails", headers=headers)
        emails = email_resp.json() if email_resp.is_success else []

        primary_email = user_data.get("email") or ""
        for em in emails:
            if em.get("primary") and em.get("verified"):
                primary_email = em.get("email")
                break

        return user_data, primary_email

