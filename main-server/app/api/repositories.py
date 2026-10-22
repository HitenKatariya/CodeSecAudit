"""Repositories API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import RepositoryResponse
from app.db.models.github import Repository
from app.db.models.review import Finding, Review
from app.db.session import get_db
from app.security.tenant import TenantContext, get_tenant_context

router = APIRouter(prefix="/v1/repositories", tags=["Repositories"])


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Repository).where(Repository.organization_id == tenant.organization.id)
    repos = (await db.execute(stmt)).scalars().all()

    result = []
    for repo in repos:
        # Aggregate findings across reviews for this repo
        f_stmt = (
            select(Finding.severity, func.count(Finding.id))
            .join(Review, Review.id == Finding.review_id)
            .where(Review.repository_id == repo.id)
            .group_by(Finding.severity)
        )
        counts = dict((await db.execute(f_stmt)).all())

        crit = counts.get("critical", 0)
        high = counts.get("high", 0)
        med = counts.get("medium", 0)
        total_open = crit + high + med

        pr_stmt = select(func.count(Review.id)).where(Review.repository_id == repo.id)
        pr_count = (await db.execute(pr_stmt)).scalar() or 0

        score = max(20, 100 - (crit * 25 + high * 15 + med * 5))
        status = "Blocked" if crit > 0 else ("Warning" if high > 0 else "Protected")

        result.append(
            RepositoryResponse(
                id=repo.id,
                name=repo.full_name.split("/")[-1] if "/" in repo.full_name else repo.full_name,
                full_name=repo.full_name,
                github_repo_id=repo.github_repo_id,
                is_private=repo.is_private,
                language="TypeScript / Python",
                security_score=score,
                critical_count=crit,
                high_count=high,
                medium_count=med,
                open_findings_count=total_open,
                pr_count=pr_count,
                last_scan="1 hour ago" if total_open > 0 else "Recent",
                status=status,
            )
        )
    return result


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Repository).where(
        Repository.organization_id == tenant.organization.id,
        (Repository.id == repo_id)
        | (Repository.full_name == repo_id)
        | (Repository.full_name.endswith("/" + repo_id)),
    )
    repo = (await db.execute(stmt)).scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    f_stmt = (
        select(Finding.severity, func.count(Finding.id))
        .join(Review, Review.id == Finding.review_id)
        .where(Review.repository_id == repo.id)
        .group_by(Finding.severity)
    )
    counts = dict((await db.execute(f_stmt)).all())

    crit = counts.get("critical", 0)
    high = counts.get("high", 0)
    med = counts.get("medium", 0)
    total_open = crit + high + med

    pr_stmt = select(func.count(Review.id)).where(Review.repository_id == repo.id)
    pr_count = (await db.execute(pr_stmt)).scalar() or 0

    score = max(20, 100 - (crit * 25 + high * 15 + med * 5))
    status = "Blocked" if crit > 0 else ("Warning" if high > 0 else "Protected")

    return RepositoryResponse(
        id=repo.id,
        name=repo.full_name.split("/")[-1] if "/" in repo.full_name else repo.full_name,
        full_name=repo.full_name,
        github_repo_id=repo.github_repo_id,
        is_private=repo.is_private,
        language="TypeScript / Python",
        security_score=score,
        critical_count=crit,
        high_count=high,
        medium_count=med,
        open_findings_count=total_open,
        pr_count=pr_count,
        last_scan="1 hour ago" if total_open > 0 else "Recent",
        status=status,
    )
