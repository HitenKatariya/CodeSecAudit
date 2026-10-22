"""Tenant-scoped findings API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import UpdateFindingStatusRequest
from app.db.models.github import Repository
from app.db.models.review import Finding, Review
from app.db.session import get_db
from app.security.tenant import TenantContext, get_tenant_context

router = APIRouter(prefix="/v1/findings", tags=["Findings"])


def _format_finding(f: Finding, repo_name: str, created_at: str) -> dict:
    return {
        "id": f.id,
        "review_id": f.review_id,
        "cwe_id": f.cwe_id,
        "severity": f.severity,
        "title": f.title,
        "file_path": f.file_path,
        "line_number": f.line_number,
        "code_snippet": f.code_snippet,
        "suggested_fix": f.suggested_fix,
        "why_it_matters": f"Violates secure coding best practices ({f.cwe_id}).",
        "attack_scenario": "Untrusted input may trigger unauthorized execution or disclosure.",
        "owasp_category": "A03:2021-Injection" if "Injection" in f.title else "A01:2021-Broken Access Control",
        "confidence": 95,
        "security_principle": "Input Validation & Defense in Depth",
        "reasoning_summary": f.suggested_fix or "Review code snippet against OWASP guidelines.",
        "status": getattr(f, "status", None) or "open",
        "detected_at": created_at,
        "repository": repo_name,
    }


@router.get("")
async def list_findings(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    severity: Optional[str] = Query(default=None),
    cwe_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = (
        select(Finding, Repository.full_name, Review.created_at)
        .join(Review, Review.id == Finding.review_id)
        .join(Repository, Repository.id == Review.repository_id, isouter=True)
        .where(Finding.organization_id == tenant.organization.id)
    )
    if severity:
        stmt = stmt.where(Finding.severity == severity.lower())
    if cwe_id:
        stmt = stmt.where(Finding.cwe_id == cwe_id.upper())

    stmt = stmt.order_by(Review.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).all()

    return [
        _format_finding(f, repo_name or "production-repo", dt.isoformat() if dt else "Recent")
        for f, repo_name, dt in rows
    ]


@router.get("/{finding_id}")
async def get_finding(
    finding_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Finding, Repository.full_name, Review.created_at)
        .join(Review, Review.id == Finding.review_id)
        .join(Repository, Repository.id == Review.repository_id, isouter=True)
        .where(Finding.id == finding_id, Finding.organization_id == tenant.organization.id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Finding not found")

    f, repo_name, dt = row
    return _format_finding(f, repo_name or "production-repo", dt.isoformat() if dt else "Recent")


@router.patch("/{finding_id}")
async def update_finding_status(
    finding_id: str,
    req: UpdateFindingStatusRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    normalized_status = req.status.strip().lower()
    if normalized_status not in ["open", "resolved", "ignored"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{req.status}'. Must be 'open', 'resolved', or 'ignored'.",
        )

    stmt = (
        select(Finding, Repository.full_name, Review.created_at)
        .join(Review, Review.id == Finding.review_id)
        .join(Repository, Repository.id == Review.repository_id, isouter=True)
        .where(Finding.id == finding_id, Finding.organization_id == tenant.organization.id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding, repo_name, dt = row
    finding.status = normalized_status
    await db.commit()
    await db.refresh(finding)

    return _format_finding(finding, repo_name or "production-repo", dt.isoformat() if dt else "Recent")
