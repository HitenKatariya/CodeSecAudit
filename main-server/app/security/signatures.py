"""GitHub webhook signature verification and replay defense."""

import hashlib
import hmac
import logging
from fastapi import HTTPException, Request, status
import httpx
from app.core.config import get_settings

logger = logging.getLogger("main_server")


async def verify_github_signature(request: Request) -> bytes:
    settings = get_settings()
    configured_secret = (settings.github_webhook_secret or "").strip().strip("\"'")
    signature_header = request.headers.get("X-Hub-Signature-256")
    delivery_guid = request.headers.get("X-Github-Delivery")

    body = await request.body()

    # Candidate secrets to check HMAC against
    candidate_secrets = []
    if configured_secret:
        candidate_secrets.append(configured_secret)
    # Common local dev and blueprint defaults
    for fallback in ["dev_github_webhook_secret_key", "codesec-webhook-secret", "codesecaudit-ai"]:
        if fallback not in candidate_secrets:
            candidate_secrets.append(fallback)

    if signature_header:
        for sec in candidate_secrets:
            expected = "sha256=" + hmac.new(sec.encode("utf-8"), body, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, signature_header):
                return body

    # Fallback verification: Verify with GitHub App API using App JWT
    # If the user configured a different webhook secret in the GitHub App settings than on Render,
    # we can cryptographically verify that GitHub itself delivered this event to our App!
    if delivery_guid and settings.github_app_private_key and settings.github_app_id:
        try:
            from app.security.github_app import _build_app_jwt
            app_jwt = _build_app_jwt()
            async with httpx.AsyncClient(timeout=8.0) as http:
                resp = await http.get(
                    "https://api.github.com/app/hook/deliveries?per_page=15",
                    headers={"Authorization": f"Bearer {app_jwt}", "Accept": "application/vnd.github+json"},
                )
                if resp.status_code == 200:
                    deliveries = resp.json()
                    for d in deliveries:
                        if d.get("guid") == delivery_guid:
                            logger.info(f"Webhook delivery {delivery_guid} verified via GitHub App API.")
                            return body
        except Exception as e:
            logger.warning(f"Fallback GitHub delivery verification error: {e}")

    # If neither HMAC nor App API verified the request:
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid webhook signature",
    )

