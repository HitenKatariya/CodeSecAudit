"""Organization team members API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import TeamMemberResponse
from app.db.models.organization import Membership
from app.db.models.user import User
from app.db.session import get_db
from app.security.tenant import TenantContext, get_tenant_context

router = APIRouter(prefix="/v1/team", tags=["Team"])


@router.get("", response_model=list[TeamMemberResponse])
async def list_team_members(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == tenant.organization.id)
        .order_by(User.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    result = []
    for user, role in rows:
        result.append(
            TeamMemberResponse(
                id=user.id,
                name=user.username,
                email=user.email or f"{user.username}@codesec.ai",
                role=role.capitalize(),
                avatar=user.avatar_url or f"https://avatars.githubusercontent.com/u/{user.github_id}?v=4",
                last_active="Active now",
            )
        )
    return result
