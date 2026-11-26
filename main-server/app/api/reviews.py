"""Tenant-scoped review API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import FindingItem, ManualReviewRequest, ReviewDetailResponse
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.models.github import Repository
from app.db.models.review import Finding, Review, ReviewJob
from app.db.session import get_db
from app.jobs.queue import enqueue_review_job
from app.reviews.github_sync import ensure_org_history_synced, sync_org_github_reviews
from app.security.org_sync import reconcile_user_organization
from app.security.tenant import TenantContext, get_tenant_context

router = APIRouter(prefix="/v1/reviews", tags=["Reviews"])


def _extract_pr_title(summary: str, pr_number: int) -> str:
    if " — " in (summary or ""):
        candidate = summary.split(" — ", 1)[0].strip()
        if candidate and not candidate.startswith(("Found ", "No security issues")):
            return candidate
    return f"Security Audit PR #{pr_number or 1}"


def _to_finding_item(f: Finding) -> FindingItem:
    return FindingItem(
        id=f.id,
        review_id=f.review_id,
        cwe_id=f.cwe_id,
        severity=f.severity,
        title=f.title,
        file_path=f.file_path,
        line_number=f.line_number,
        code_snippet=f.code_snippet,
        suggested_fix=f.suggested_fix,
        status=getattr(f, "status", None) or "open",
    )


def _to_review_response(r: Review, repo_name: str, items: list[FindingItem]) -> ReviewDetailResponse:
    pr_link = f"https://github.com/{repo_name}/pull/{r.pr_number}" if r.pr_number and "/" in repo_name else None
    return ReviewDetailResponse(
        id=r.id,
        repository_id=r.repository_id,
        repo_full_name=repo_name,
        pr_url=pr_link,
        pr_title=_extract_pr_title(r.summary, r.pr_number),
        pr_number=r.pr_number,
        commit_sha=r.commit_sha,
        risk_score=r.risk_score,
        verdict=r.verdict,
        summary=r.summary,
        guidance_available=r.guidance_available,
        created_at=r.created_at.isoformat(),
        findings=items,
    )


@router.post("/sync-github")
async def sync_github_reviews(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await reconcile_user_organization(db, tenant.user, tenant.organization.id)
    res = await sync_org_github_reviews(db, tenant.organization.id)
    try:
        redis = await get_redis_service(get_settings().redis_url).get_async()
        await redis.setex(f"gh_history_synced_v3:{tenant.organization.id}", 3600, "1")
    except Exception:
        pass
    return res


@router.get("", response_model=list[ReviewDetailResponse])
async def list_reviews(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        if await reconcile_user_organization(db, tenant.user, tenant.organization.id):
            await db.commit()
    except Exception:
        await db.rollback()

    await ensure_org_history_synced(db, tenant.organization.id)

    stmt = (
        select(Review)
        .where(Review.organization_id == tenant.organization.id)
        .order_by(Review.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    reviews = (await db.execute(stmt)).scalars().all()
    if not reviews:
        return []

    repo_ids = {r.repository_id for r in reviews}
    repos = (await db.execute(select(Repository).where(Repository.id.in_(repo_ids)))).scalars().all()
    repo_name_map = {r.id: r.full_name for r in repos}

    findings = (await db.execute(select(Finding).where(Finding.review_id.in_([r.id for r in reviews])))).scalars().all()
    by_review: dict[str, list[FindingItem]] = {r.id: [] for r in reviews}
    for f in findings:
        by_review.setdefault(f.review_id, []).append(_to_finding_item(f))

    return [_to_review_response(r, repo_name_map.get(r.repository_id, r.repository_id), by_review.get(r.id, [])) for r in reviews]


@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review_detail(
    review_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    if review_id.isdigit():
        stmt = (
            select(Review)
            .where(Review.organization_id == tenant.organization.id, (Review.id == review_id) | (Review.pr_number == int(review_id)))
            .order_by(Review.created_at.desc())
        )
    else:
        stmt = select(Review).where(Review.id == review_id, Review.organization_id == tenant.organization.id)

    review = (await db.execute(stmt)).scalars().first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    repo = (await db.execute(select(Repository).where(Repository.id == review.repository_id))).scalar_one_or_none()
    repo_name = repo.full_name if repo else review.repository_id
    findings = (await db.execute(select(Finding).where(Finding.review_id == review.id))).scalars().all()
    return _to_review_response(review, repo_name, [_to_finding_item(f) for f in findings])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_manual_review(
    req: ManualReviewRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    job = ReviewJob(
        organization_id=tenant.organization.id,
        repository_id=req.repository_id,
        pr_number=0,
        commit_sha="manual",
        status="queued",
    )
    db.add(job)
    await db.commit()

    await enqueue_review_job({
        "job_id": job.id,
        "organization_id": tenant.organization.id,
        "repository_id": req.repository_id,
        "pr_number": 0,
        "commit_sha": "manual",
        "code_content": req.code_content,
        "file_path": req.file_path,
    })
    return {"status": "enqueued", "job_id": job.id}
