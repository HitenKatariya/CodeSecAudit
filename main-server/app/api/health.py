"""Health and version endpoints."""

import httpx
from fastapi import APIRouter, HTTPException, status
from app.api.schemas import HealthResponse, VersionResponse
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.session import is_db_healthy

router = APIRouter(tags=["Health & Version"])


@router.get("/health/live")
def health_live():
    return {"status": "ok"}


@router.get("/health/ready", response_model=HealthResponse)
async def health_ready():
    settings = get_settings()
    db_ok = await is_db_healthy()
    redis_service = get_redis_service(settings.redis_url)
    redis_ok = await redis_service.is_healthy()

    rag_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.rag_service_url.rstrip('/')}/health/live")
            rag_ok = resp.status_code == 200
    except Exception:
        rag_ok = False

    pg_status = "connected" if db_ok else "unreachable"
    redis_status = "connected" if redis_ok else "unreachable"
    rag_status = "connected" if rag_ok else "unreachable"

    if not (db_ok and redis_ok):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"postgres": pg_status, "redis": redis_status, "rag_service": rag_status},
        )

    return HealthResponse(
        status="ready",
        postgres=pg_status,
        redis=redis_status,
        rag_service=rag_status,
    )


@router.get("/version", response_model=VersionResponse)
def version():
    settings = get_settings()
    return VersionResponse(
        service="main-server",
        version=settings.app_version,
        git_sha=settings.git_sha,
    )
