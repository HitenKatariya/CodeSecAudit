"""Admin-only sanitized log tailing endpoints from Redis Streams."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import LogEntry
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.models.audit import AuditEvent
from app.db.models.user import User
from app.db.session import get_db
from app.security.tenant import require_system_admin

router = APIRouter(tags=["Admin Logs"])


async def _tail_stream(stream_key: str, admin_user: User, limit: int, request: Request, db: AsyncSession) -> list[LogEntry]:
    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    entries = await redis_service.tail_log_stream(stream_key, limit=limit)

    # Record access in audit log
    client_ip = request.client.host if request.client else "unknown"
    db.add(AuditEvent(
        user_id=admin_user.id,
        action="view_logs",
        resource_type="redis_stream",
        resource_id=stream_key,
        ip_address=client_ip,
        details_json=f'{{"stream": "{stream_key}", "limit": {limit}}}',
    ))
    await db.commit()

    return [
        LogEntry(
            id=e.get("id", ""),
            timestamp=e.get("timestamp", ""),
            level=e.get("level", "INFO"),
            message=e.get("message", ""),
            service=e.get("service", "unknown"),
        )
        for e in entries
    ]


@router.get("/main-server-logs", response_model=list[LogEntry])
async def get_main_server_logs(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    admin_user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _tail_stream("log:main-server", admin_user, limit, request, db)


@router.get("/client-server-logs", response_model=list[LogEntry])
async def get_client_server_logs(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    admin_user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _tail_stream("log:client", admin_user, limit, request, db)


@router.get("/rag-server-logs", response_model=list[LogEntry])
async def get_rag_server_logs(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    admin_user: User = Depends(require_system_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _tail_stream("log:rag-server", admin_user, limit, request, db)
