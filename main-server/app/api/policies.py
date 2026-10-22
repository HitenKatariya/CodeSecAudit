"""Tenant security policies API endpoints."""

import json
from fastapi import APIRouter, Depends
from app.api.schemas import SecurityPolicySchema
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.security.tenant import TenantContext, get_tenant_context

router = APIRouter(prefix="/v1/policies", tags=["Policies"])


@router.get("", response_model=SecurityPolicySchema)
async def get_security_policy(tenant: TenantContext = Depends(get_tenant_context)):
    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    client = await redis_service.get_async()

    raw = await client.get(f"org_policy:{tenant.organization.id}")
    if raw:
        try:
            return SecurityPolicySchema(**json.loads(raw))
        except Exception:
            pass

    return SecurityPolicySchema()


@router.put("", response_model=SecurityPolicySchema)
async def update_security_policy(
    policy: SecurityPolicySchema,
    tenant: TenantContext = Depends(get_tenant_context),
):
    settings = get_settings()
    redis_service = get_redis_service(settings.redis_url)
    client = await redis_service.get_async()

    await client.set(f"org_policy:{tenant.organization.id}", policy.model_dump_json())
    return policy
