"""Tenant isolation and role-based access control dependencies."""

from dataclasses import dataclass
from typing import Any
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.organization import Membership, Organization
from app.db.models.user import User
from app.db.session import get_db
from app.security.sessions import get_current_session, get_current_user


@dataclass
class TenantContext:
    user: User
    organization: Organization
    role: str  # admin, member


async def get_tenant_context(
    user: User = Depends(get_current_user),
    session: dict[str, Any] = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    org_id = session.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active organization in session")

    stmt = (
        select(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Organization.id == org_id, Membership.user_id == user.id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this organization")

    org, role = row
    return TenantContext(user=user, organization=org, role=role)


async def require_system_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user
