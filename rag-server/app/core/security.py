"""Internal service authentication security controls."""

import hmac
from fastapi import Header, HTTPException, status
from app.core.config import get_settings


def verify_internal_token(
    x_internal_rag_token: str | None = Header(default=None, alias="X-Internal-RAG-Token"),
) -> None:
    settings = get_settings()
    expected = settings.rag_service_token

    if not x_internal_rag_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required internal service token header",
        )

    if not hmac.compare_digest(x_internal_rag_token.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service token",
        )
