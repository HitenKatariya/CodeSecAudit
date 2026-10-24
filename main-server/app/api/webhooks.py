"""GitHub App webhook receiver with signature validation and idempotency."""

import hashlib
import json
import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.models.github import GitHubInstallation, Repository, WebhookDelivery
from app.db.models.organization import Organization
from app.db.models.review import ReviewJob
from app.db.session import get_db
from app.jobs.queue import enqueue_review_job
from app.security.signatures import verify_github_signature

logger = logging.getLogger("main_server")
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
singular_router = APIRouter(prefix="/webhook", tags=["Webhooks"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
@singular_router.post("", status_code=status.HTTP_202_ACCEPTED)
@singular_router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    body: bytes = Depends(verify_github_signature),
    db: AsyncSession = Depends(get_db),

    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
):
    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)

    # 1. Fast Redis replay protection
    if await redis_service.is_webhook_processed(x_github_delivery):
        return {"status": "duplicate_ignored"}

    payload_hash = hashlib.sha256(body).hexdigest()

    # 2. Record delivery in PostgreSQL
    delivery = WebhookDelivery(
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        status="received",
        payload_hash=payload_hash,
    )
    db.add(delivery)
    await db.commit()

    if x_github_event != "pull_request":
        return {"status": "event_ignored", "event": x_github_event}

    payload = json.loads(body)
    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "action_ignored", "action": action}

    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})
    install_data = payload.get("installation", {})

    gh_install_id = str(install_data.get("id", ""))
    gh_repo_id = str(repo_data.get("id", ""))
    repo_name = repo_data.get("full_name", "")
    pr_number = pr_data.get("number", 0)
    commit_sha = (pr_data.get("head") or {}).get("sha", "")

    # Resolve organization from installation
    inst_stmt = select(GitHubInstallation).where(GitHubInstallation.installation_id == gh_install_id)
    inst = (await db.execute(inst_stmt)).scalar_one_or_none()
    if not inst:
        account_data = install_data.get("account") or repo_data.get("owner") or {}
        account_login = account_data.get("login", "")
        # Match organization or fallback to first organization in database
        org = None
        if account_login:
            org_stmt = select(Organization).where(Organization.slug.ilike(f"{account_login.lower()}%"))
            org = (await db.execute(org_stmt)).scalars().first()
        if not org:
            org = (await db.execute(select(Organization))).scalars().first()
        if not org:
            org = Organization(name=f"{account_login or 'Default'}'s Org", slug=f"{(account_login or 'default').lower()}-org")
            db.add(org)
            await db.flush()

        inst = GitHubInstallation(
            installation_id=gh_install_id,
            organization_id=org.id,
            account_login=account_login or "unknown",
            target_type=install_data.get("target_type", "User"),
        )
        db.add(inst)
        await db.flush()
        logger.info(f"Auto-linked installation {gh_install_id} to organization {org.id}")


    # Resolve or register repository
    repo_stmt = select(Repository).where(Repository.github_repo_id == gh_repo_id)
    repo = (await db.execute(repo_stmt)).scalar_one_or_none()
    if not repo:
        repo = Repository(
            organization_id=inst.organization_id,
            github_repo_id=gh_repo_id,
            full_name=repo_name,
            is_private=repo_data.get("private", False),
        )
        db.add(repo)
        await db.flush()

    # Create ReviewJob
    job = ReviewJob(
        organization_id=inst.organization_id,
        repository_id=repo.id,
        pr_number=pr_number,
        commit_sha=commit_sha,
        status="queued",
    )
    db.add(job)
    await db.commit()

    # 3. Enqueue immediately - the diff fetch and the review itself happen in
    # the worker, never inside this request. GitHub expects a webhook ACK
    # within ~10s; the review (diff fetch + regex scan + optional LLM pass +
    # RAG lookups + posting the result comment) can legitimately take much
    # longer than that, especially on a large PR or a slow LLM provider.
    job_payload = {
        "job_id": job.id,
        "organization_id": inst.organization_id,
        "repository_id": repo.id,
        "pr_number": pr_number,
        "commit_sha": commit_sha,
        "is_diff": True,
        "repo_full_name": repo_name,
        "installation_id": gh_install_id,
    }
    await enqueue_review_job(job_payload)

    return {"status": "enqueued", "job_id": job.id}
