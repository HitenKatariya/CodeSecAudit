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


@router.get("/health/worker-status")
async def health_worker_status():
    from sqlalchemy import select
    from app.db.models.review import ReviewJob
    from app.db.session import get_session_factory

    settings = get_settings()
    jwt_status = "ok"
    try:
        from app.security.github_app import _build_app_jwt

        _ = _build_app_jwt()
    except Exception as e:
        jwt_status = f"error: {type(e).__name__}: {str(e)}"

    job_list = []
    try:
        factory = get_session_factory()
        async with factory() as db:
            stmt = select(ReviewJob).order_by(ReviewJob.created_at.desc()).limit(5)
            jobs = (await db.execute(stmt)).scalars().all()
            job_list = [
                {
                    "id": j.id,
                    "pr_number": j.pr_number,
                    "status": j.status,
                    "error_message": j.error_message,
                    "created_at": j.created_at.isoformat() if j.created_at else None,
                }
                for j in jobs
            ]
    except Exception as e:
        job_list = [{"error": str(e)}]

    return {
        "app_id": str(settings.github_app_id or "").strip(),
        "has_private_key": bool(settings.github_app_private_key),
        "private_key_len": len(settings.github_app_private_key or ""),
        "jwt_status": jwt_status,
        "run_worker_inline": settings.run_worker_inline,
        "recent_jobs": job_list,
    }


@router.post("/health/retry-job/{job_id}")
async def retry_review_job(job_id: str):
    from sqlalchemy import select
    from app.db.models.github import GitHubInstallation, Repository
    from app.db.models.review import ReviewJob
    from app.db.session import get_session_factory
    from app.jobs.queue import enqueue_review_job

    factory = get_session_factory()
    async with factory() as db:
        stmt = select(ReviewJob).where(ReviewJob.id == job_id)
        job = (await db.execute(stmt)).scalar_one_or_none()
        if not job:
            return {"error": "job not found"}

        repo = (await db.execute(select(Repository).where(Repository.id == job.repository_id))).scalar_one_or_none()
        inst = (await db.execute(select(GitHubInstallation).where(GitHubInstallation.organization_id == job.organization_id))).scalars().first()

        job.status = "queued"
        job.error_message = None
        await db.commit()

        payload = {
            "job_id": job.id,
            "organization_id": job.organization_id,
            "repository_id": job.repository_id,
            "pr_number": job.pr_number,
            "commit_sha": job.commit_sha,
            "is_diff": True,
            "repo_full_name": repo.full_name if repo else "OMCHOKSI108/CodeSecurityAuditAgent",
            "installation_id": inst.installation_id if inst else "174581234",
        }
        await enqueue_review_job(payload)
        return {"status": "re-enqueued", "job_id": job.id}
