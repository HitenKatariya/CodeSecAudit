"""Tenant security policies API endpoints."""

import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import SecurityPolicySchema
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.models.organization import Organization
from app.db.models.review import Finding, Review
from app.db.session import get_db
from app.reviews.risk import calculate_risk_score, decide_verdict, filter_findings_by_policy
from app.security.tenant import TenantContext, get_tenant_context

router = APIRouter(prefix="/v1/policies", tags=["Policies"])


@router.get("", response_model=SecurityPolicySchema)
async def get_security_policy(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    client = await redis_service.get_async()
    cache_key = f"org_policy:{tenant.organization.id}"

    raw = await client.get(cache_key)
    if raw:
        try:
            return SecurityPolicySchema(**json.loads(raw))
        except Exception:
            pass

    org = (await db.execute(select(Organization).where(Organization.id == tenant.organization.id))).scalar_one_or_none()
    if org and org.policy_json:
        try:
            schema = SecurityPolicySchema(**json.loads(org.policy_json))
            await client.set(cache_key, schema.model_dump_json())
            return schema
        except Exception:
            pass

    return SecurityPolicySchema()


@router.put("", response_model=SecurityPolicySchema)
async def update_security_policy(
    policy: SecurityPolicySchema,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    policy_json = policy.model_dump_json()
    org = (await db.execute(select(Organization).where(Organization.id == tenant.organization.id))).scalar_one_or_none()
    if org is not None:
        org.policy_json = policy_json

    # Dynamically re-evaluate recorded reviews so threshold/toggle updates show up immediately
    reviews = (await db.execute(select(Review).where(Review.organization_id == tenant.organization.id))).scalars().all()
    if reviews:
        findings = (await db.execute(select(Finding).where(Finding.organization_id == tenant.organization.id))).scalars().all()
        by_review: dict[str, list[dict]] = {}
        for f in findings:
            by_review.setdefault(f.review_id, []).append({
                "cwe_id": f.cwe_id,
                "severity": f.severity,
                "title": f.title,
            })
        for rev in reviews:
            active_findings = filter_findings_by_policy(by_review.get(rev.id, []), policy)
            effective_risk = calculate_risk_score(active_findings) if by_review.get(rev.id) else rev.risk_score
            rev.risk_score = effective_risk
            rev.verdict = decide_verdict(effective_risk, findings=active_findings, policy=policy)

    await db.commit()

    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    client = await redis_service.get_async()
    await client.set(f"org_policy:{tenant.organization.id}", policy_json)
    return policy
