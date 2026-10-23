"""GitHub App JWT signing and installation access token retrieval."""

import logging
import time
import jwt
import httpx
from app.core.config import get_settings
from app.core.redis import get_redis_service

logger = logging.getLogger("main_server")

GITHUB_API_BASE = "https://api.github.com"
_TOKEN_CACHE_KEY = "github_app:install_token:{installation_id}"


def _format_private_key(raw_key: str) -> str:
    if not raw_key:
        return ""
    key = raw_key.strip().strip("\"'").strip()
    if "\\n" in key:
        key = key.replace("\\n", "\n")
    if "BEGIN" not in key:
        clean_body = "\n".join(line.strip() for line in key.splitlines() if line.strip())
        key = f"-----BEGIN RSA PRIVATE KEY-----\n{clean_body}\n-----END RSA PRIVATE KEY-----\n"
    if not key.endswith("\n"):
        key += "\n"
    return key


def _build_app_jwt() -> str:
    settings = get_settings()
    now = int(time.time())
    app_id = str(settings.github_app_id or "").strip().strip("\"'")
    payload = {"iat": now - 60, "exp": now + 540, "iss": app_id}
    private_key = _format_private_key(settings.github_app_private_key)
    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(installation_id: str) -> str:
    """Return a cached or freshly minted GitHub App installation access token."""
    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    client = await redis_service.get_async()

    cache_key = _TOKEN_CACHE_KEY.format(installation_id=installation_id)
    cached = await client.get(cache_key)
    if cached:
        return cached

    app_jwt = _build_app_jwt()
    url = f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens"
    headers = {"Authorization": f"Bearer {app_jwt}", "Accept": "application/vnd.github+json"}

    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.post(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    token = data["token"]
    # Tokens are valid for 1 hour; cache for 50 minutes so we never serve one near expiry.
    await client.setex(cache_key, 3000, token)
    return token


async def fetch_pull_request_diff(full_name: str, pr_number: int, installation_id: str) -> str:
    """Fetch the unified diff for a pull request using an installation token."""
    token = await get_installation_token(installation_id)
    url = f"{GITHUB_API_BASE}/repos/{full_name}/pulls/{pr_number}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3.diff"}

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(url, headers=headers)
        if resp.status_code != 200:
            logger.warning(f"Failed to fetch PR diff for {full_name}#{pr_number}: {resp.status_code}")
            return ""
        return resp.text


async def post_pr_comment(full_name: str, pr_number: int, installation_id: str, body: str) -> bool:
    """Post a comment on a pull request (PR comments live under the issues API)."""
    token = await get_installation_token(installation_id)
    url = f"{GITHUB_API_BASE}/repos/{full_name}/issues/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(url, headers=headers, json={"body": body})
        if resp.status_code != 201:
            logger.warning(f"Failed to post PR comment on {full_name}#{pr_number}: {resp.status_code} {resp.text}")
            return False
        return True


async def get_installation_details(installation_id: str) -> dict:
    """Fetch metadata for an installed GitHub App instance using app JWT."""
    try:
        app_jwt = _build_app_jwt()
    except Exception as e:
        logger.warning(f"Could not build App JWT: {e}")
        return {}

    url = f"{GITHUB_API_BASE}/app/installations/{installation_id}"
    headers = {"Authorization": f"Bearer {app_jwt}", "Accept": "application/vnd.github+json"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch installation details for {installation_id}: {resp.status_code}")
                return {}
            return resp.json()
    except Exception as e:
        logger.warning(f"Error fetching installation details: {e}")
        return {}


async def sync_installation_repositories(installation_id: str) -> list[dict]:
    """Fetch repositories accessible by a given GitHub App installation."""
    try:
        token = await get_installation_token(installation_id)
        url = f"{GITHUB_API_BASE}/installation/repositories"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch installation repositories for {installation_id}: {resp.status_code}")
                return []
            data = resp.json()
            return data.get("repositories", [])
    except Exception as e:
        logger.warning(f"Error fetching installation repositories for {installation_id}: {e}")
        return []

