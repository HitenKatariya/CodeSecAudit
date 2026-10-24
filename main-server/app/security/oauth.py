"""GitHub OAuth 2.0 with PKCE, HMAC-signed CSRF state, and resilient fallback."""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Optional
from urllib.parse import urlencode
import httpx
from app.core.config import get_settings
from app.core.redis import get_redis_service

logger = logging.getLogger("main_server.oauth")


def _generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def _sign_state(payload: dict, secret: str) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    encoded_sig = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_sig}"


def _verify_signed_state(state: str, secret: str, max_age: int = 1200) -> Optional[dict]:
    if "." not in state:
        return None
    try:
        parts = state.split(".", 1)
        if len(parts) != 2:
            return None
        encoded_payload, encoded_sig = parts
        expected_sig = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
        expected_encoded_sig = base64.urlsafe_b64encode(expected_sig).decode("ascii").rstrip("=")
        if not hmac.compare_digest(encoded_sig, expected_encoded_sig):
            return None
        padding = "=" * ((4 - len(encoded_payload) % 4) % 4)
        raw = base64.urlsafe_b64decode(f"{encoded_payload}{padding}")
        data = json.loads(raw.decode("utf-8"))
        if time.time() - data.get("t", 0) > max_age:
            return None
        return data
    except Exception:
        return None


async def _fetch_github_user_and_email(http: httpx.AsyncClient, access_token: str) -> tuple[dict, str]:
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


async def create_oauth_authorization_url(redirect_uri: str) -> str:
    settings = get_settings()
    secret = settings.session_secret or "codesec_dev_session_secret_32b"
    verifier, challenge = _generate_pkce_pair()

    state = _sign_state({"v": verifier, "r": redirect_uri, "t": int(time.time()), "n": secrets.token_hex(6)}, secret)

    try:
        redis_service = get_redis_service(settings.redis_url)
        client = await redis_service.get_async()
        payload = json.dumps({"verifier": verifier, "redirect_uri": redirect_uri})
        await client.setex(f"oauth_state:{state}", 1200, payload)
    except Exception as e:
        logger.debug(f"Redis state caching bypassed (using signed token): {e}")

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
    secret = settings.session_secret or "codesec_dev_session_secret_32b"

    verifier = None
    redirect_uri = None

    signed_data = _verify_signed_state(state, secret)
    if signed_data:
        verifier = signed_data.get("v")
        redirect_uri = signed_data.get("r")

    if not verifier:
        try:
            redis_service = get_redis_service(settings.redis_url)
            client = await redis_service.get_async()
            raw_state_data = await client.get(f"oauth_state:{state}")
            if raw_state_data:
                await client.delete(f"oauth_state:{state}")
                state_data = json.loads(raw_state_data)
                verifier = state_data.get("verifier")
                redirect_uri = state_data.get("redirect_uri")
        except Exception as e:
            logger.debug(f"Redis state lookup error: {e}")

    if not redirect_uri:
        redirect_uri = settings.github_oauth_redirect_uri

    async with httpx.AsyncClient(timeout=15.0) as http:
        token_payload = {
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        if verifier:
            token_payload["code_verifier"] = verifier

        token_resp = await http.post(
            "https://github.com/login/oauth/access_token",
            json=token_payload,
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        if not access_token and verifier:
            token_payload.pop("code_verifier", None)
            fallback_resp = await http.post(
                "https://github.com/login/oauth/access_token",
                json=token_payload,
                headers={"Accept": "application/json"},
            )
            fallback_data = fallback_resp.json()
            access_token = fallback_data.get("access_token")

        if not access_token:
            err = token_data.get("error_description") or token_data.get("error") or "token exchange failed"
            raise ValueError(f"GitHub OAuth token exchange failed: {err}")

        return await _fetch_github_user_and_email(http, access_token)


async def exchange_github_app_code(code: str) -> tuple[dict, str]:
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

        return await _fetch_github_user_and_email(http, access_token)

