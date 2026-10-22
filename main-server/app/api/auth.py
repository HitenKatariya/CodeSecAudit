"""Authentication API routes."""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import UserMeResponse
from app.core.config import get_settings
from app.db.models.organization import Membership, Organization
from app.db.models.user import User
from app.db.session import get_db
from app.security.oauth import create_oauth_authorization_url, verify_oauth_callback
from app.security.sessions import (
    SESSION_COOKIE_NAME,
    create_user_session,
    destroy_user_session,
)
from app.security.tenant import TenantContext, get_tenant_context

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


@router.get("/github/start")
async def github_auth_start():
    settings = get_settings()
    redirect_uri = settings.github_oauth_redirect_uri
    auth_url = await create_oauth_authorization_url(redirect_uri)
    return RedirectResponse(auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/github/callback")
async def github_auth_callback(
    response: Response,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    try:
        user_data, email = await verify_oauth_callback(code, state)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth verification failed: {e}")

    github_id = str(user_data["id"])
    username = user_data.get("login", "")
    avatar = user_data.get("avatar_url", "")

    # Upsert user
    stmt = select(User).where(User.github_id == github_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        user = User(github_id=github_id, username=username, email=email, avatar_url=avatar)
        db.add(user)
        await db.flush()
    else:
        user.username = username
        user.email = email
        user.avatar_url = avatar

    # Ensure personal organization
    mem_stmt = select(Membership, Organization).join(Organization).where(Membership.user_id == user.id)
    mem_row = (await db.execute(mem_stmt)).first()

    if not mem_row:
        org = Organization(name=f"{username}'s Org", slug=f"{username.lower()}-personal")
        db.add(org)
        await db.flush()
        membership = Membership(organization_id=org.id, user_id=user.id, role="admin")
        db.add(membership)
        org_id = org.id
    else:
        org_id = mem_row[1].id

    await db.commit()

    # Create opaque session
    redirect_resp = RedirectResponse(settings.next_public_app_url, status_code=status.HTTP_302_FOUND)
    await create_user_session(redirect_resp, user.id, org_id)
    return redirect_resp


@router.post("/logout")
async def logout(
    response: Response,
    codesec_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    await destroy_user_session(response, codesec_session)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserMeResponse, tags=["Current User"])
async def get_me(tenant: TenantContext = Depends(get_tenant_context)):
    return UserMeResponse(
        id=tenant.user.id,
        github_id=tenant.user.github_id,
        username=tenant.user.username,
        email=tenant.user.email,
        avatar_url=tenant.user.avatar_url,
        is_admin=tenant.user.is_admin,
        active_organization_id=tenant.organization.id,
        organization_name=tenant.organization.name,
        organization_role=tenant.role,
    )
