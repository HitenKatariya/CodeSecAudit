"""Authentication API routes."""

import json
import secrets
from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import LoginRequest, UserMeResponse
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.models.audit import AuditEvent
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
    request: Request,
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

    # Upsert user in Postgres
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

    # Ensure personal organization in Postgres
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

    # Record login audit event
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    db.add(
        AuditEvent(
            user_id=user.id,
            organization_id=org_id,
            action="auth.login",
            resource_type="session",
            resource_id=user.id,
            ip_address=client_ip,
            details_json=json.dumps({
                "provider": "github",
                "username": username,
                "email": email,
                "organization_id": org_id,
                "user_agent": user_agent,
            }),
        )
    )

    await db.commit()

    # Create opaque session
    redirect_resp = RedirectResponse(settings.next_public_app_url, status_code=status.HTTP_302_FOUND)
    await create_user_session(redirect_resp, user.id, org_id)
    return redirect_resp


@router.post("/login", response_model=UserMeResponse, tags=["Authentication"])
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Direct/workspace user login that ensures user, organization, membership and audit logging in Postgres."""
    username = (payload.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    email = (payload.email or f"{username.lower()}@codesec.ai").strip()
    github_id = f"direct_{username.lower()}"
    avatar = f"https://avatars.githubusercontent.com/{username}"

    # Upsert user in Postgres
    stmt = select(User).where((User.github_id == github_id) | (User.username == username))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        user = User(
            github_id=github_id,
            username=username,
            email=email,
            avatar_url=avatar,
            is_admin=True,
        )
        db.add(user)
        await db.flush()
    else:
        user.username = username
        if email:
            user.email = email

    # Ensure organization and membership in Postgres
    mem_stmt = (
        select(Membership, Organization)
        .join(Organization, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id)
    )
    mem_row = (await db.execute(mem_stmt)).first()

    if not mem_row:
        org_name = payload.organization_name or f"{username}'s Workspace"
        org_slug = f"{username.lower().replace(' ', '-')}-workspace"
        existing_org = (await db.execute(select(Organization).where(Organization.slug == org_slug))).scalar_one_or_none()
        if existing_org:
            org_slug = f"{org_slug}-{secrets.token_hex(3)}"

        org = Organization(name=org_name, slug=org_slug)
        db.add(org)
        await db.flush()
        membership = Membership(organization_id=org.id, user_id=user.id, role="admin")
        db.add(membership)
        org_id = org.id
        org_title = org.name
        org_role = "admin"
    else:
        membership, org = mem_row
        org_id = org.id
        org_title = org.name
        org_role = membership.role

    # Record login audit event
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    db.add(
        AuditEvent(
            user_id=user.id,
            organization_id=org_id,
            action="auth.login",
            resource_type="session",
            resource_id=user.id,
            ip_address=client_ip,
            details_json=json.dumps({
                "provider": "direct",
                "username": username,
                "email": user.email,
                "organization_id": org_id,
                "organization_name": org_title,
                "user_agent": user_agent,
            }),
        )
    )

    await db.commit()

    # Create session token in Redis and set HttpOnly cookie
    await create_user_session(response, user.id, org_id)

    return UserMeResponse(
        id=user.id,
        github_id=user.github_id,
        username=user.username,
        email=user.email,
        avatar_url=user.avatar_url,
        is_admin=user.is_admin,
        active_organization_id=org_id,
        organization_name=org_title,
        organization_role=org_role,
    )


@router.post("/demo-login", response_model=UserMeResponse, tags=["Authentication"])
async def demo_login(
    request: Request,
    response: Response,
    payload: Optional[LoginRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Convenience alias for demo/direct login."""
    req = payload or LoginRequest(username="omchoksi", email="om@codesec.ai")
    return await login(payload=req, request=request, response=response, db=db)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    codesec_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    if codesec_session:
        settings = get_settings()
        redis_service = get_redis_service(settings.redis_url)
        session_data = await redis_service.get_session(codesec_session)
        if session_data:
            user_id = session_data.get("user_id")
            org_id = session_data.get("organization_id")
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            try:
                db.add(
                    AuditEvent(
                        user_id=user_id,
                        organization_id=org_id,
                        action="auth.logout",
                        resource_type="session",
                        resource_id=user_id,
                        ip_address=client_ip,
                        details_json=json.dumps({"user_agent": user_agent}),
                    )
                )
                await db.commit()
            except Exception:
                pass
        await destroy_user_session(response, codesec_session)
    else:
        await destroy_user_session(response, None)
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
