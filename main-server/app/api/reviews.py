"""Tenant-scoped review API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import FindingItem, ManualReviewRequest, ReviewDetailResponse
from app.db.models.github import Repository
from app.db.models.review import Finding, Review, ReviewJob
from app.db.session import get_db
from app.jobs.queue import enqueue_review_job
from app.security.tenant import TenantContext, get_tenant_context

router = APIRouter(prefix="/v1/reviews", tags=["Reviews"])


@router.get("", response_model=list[ReviewDetailResponse])
async def list_reviews(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = (
        select(Review)
        .where(Review.organization_id == tenant.organization.id)
        .order_by(Review.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    response = []
    for r in reviews:
        response.append(
            ReviewDetailResponse(
                id=r.id,
                repository_id=r.repository_id,
                pr_number=r.pr_number,
                commit_sha=r.commit_sha,
                risk_score=r.risk_score,
                verdict=r.verdict,
                summary=r.summary,
                guidance_available=r.guidance_available,
                created_at=r.created_at.isoformat(),
                findings=[],
            )
        )
    return response


@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review_detail(
    review_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    if review_id.isdigit():
        stmt = (
            select(Review)
            .where(
                Review.organization_id == tenant.organization.id,
                (Review.id == review_id) | (Review.pr_number == int(review_id)),
            )
            .order_by(Review.created_at.desc())
        )
    else:
        stmt = select(Review).where(Review.id == review_id, Review.organization_id == tenant.organization.id)

    review = (await db.execute(stmt)).scalars().first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    repo_stmt = select(Repository).where(Repository.id == review.repository_id)
    repo = (await db.execute(repo_stmt)).scalar_one_or_none()
    repo_name = repo.full_name if repo else review.repository_id

    finding_stmt = select(Finding).where(Finding.review_id == review.id)
    findings = (await db.execute(finding_stmt)).scalars().all()

    finding_items = [
        FindingItem(
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
        for f in findings
    ]

    return ReviewDetailResponse(
        id=review.id,
        repository_id=repo_name,
        pr_number=review.pr_number,
        commit_sha=review.commit_sha,
        risk_score=review.risk_score,
        verdict=review.verdict,
        summary=review.summary,
        guidance_available=review.guidance_available,
        created_at=review.created_at.isoformat(),
        findings=finding_items,
    )


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
