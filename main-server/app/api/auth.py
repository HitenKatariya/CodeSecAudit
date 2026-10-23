"""Authentication API routes."""

import json
import logging
import secrets
from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import LoginRequest, UserMeResponse
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.models.audit import AuditEvent, UsageEvent
from app.db.models.github import GitHubInstallation, Repository, WebhookDelivery
from app.db.models.organization import Membership, Organization
from app.db.models.review import Finding, Review, ReviewJob
from app.db.models.user import User
from app.db.session import get_db
from app.security.github_app import (
    get_installation_details,
    sync_installation_repositories,
    uninstall_github_app,
)
from app.security.oauth import (
    create_oauth_authorization_url,
    exchange_github_app_code,
    verify_oauth_callback,
)
from app.security.sessions import (
    SESSION_COOKIE_NAME,
    create_user_session,
    destroy_user_session,
)
from app.security.tenant import TenantContext, get_tenant_context

logger = logging.getLogger("main_server")


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
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    installation_id: Optional[str] = Query(None),
    setup_action: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    user_data = None
    email = ""

    # 1. Exchange authorization code
    if state and code:
        # Standard PKCE OAuth callback from "Sign in with GitHub"
        try:
            user_data, email = await verify_oauth_callback(code, state)
        except Exception as e:
            logger.warning(f"Standard OAuth verification failed: {e}")
            raise HTTPException(status_code=400, detail=f"OAuth verification failed: {e}")
    elif code:
        # GitHub App installation callback with authorization code
        try:
            user_data, email = await exchange_github_app_code(code)
        except Exception as e:
            logger.warning(f"GitHub App code exchange failed: {e}")

    # 2. If code wasn't provided or didn't yield user, inspect existing session cookie
    user = None
    org_id = None
    if not user_data:
        cookie_val = request.cookies.get(SESSION_COOKIE_NAME)
        if cookie_val:
            try:
                redis_service = get_redis_service(settings.redis_url)
                session_data = await redis_service.get_session(cookie_val)
                if session_data and "user_id" in session_data:
                    u_stmt = select(User).where(User.id == session_data["user_id"])
                    user = (await db.execute(u_stmt)).scalar_one_or_none()
                    if user:
                        org_id = session_data.get("organization_id")
            except Exception as e:
                logger.warning(f"Failed to resolve existing session during install callback: {e}")

    # 3. If still no user and installation_id is provided, resolve from GitHub App installation
    if not user and not user_data and installation_id:
        try:
            inst_details = await get_installation_details(str(installation_id))
            acc = inst_details.get("account", {})
            if acc and acc.get("id"):
                user_data = {
                    "id": str(acc.get("id")),
                    "login": acc.get("login", ""),
                    "avatar_url": acc.get("avatar_url", ""),
                    "type": acc.get("type", "User"),
                }
                email = f"{acc.get('login', '').lower()}@codesec.ai"
        except Exception as e:
            logger.warning(f"Failed to resolve user from installation {installation_id}: {e}")

    if not user and not user_data:
        login_url = f"{settings.next_public_app_url.rstrip('/')}/login?error=oauth_failed"
        return RedirectResponse(login_url, status_code=status.HTTP_302_FOUND)

    # 4. Upsert User & Organization if user_data resolved
    if user_data:
        github_id = str(user_data["id"])
        username = user_data.get("login", "")
        avatar = user_data.get("avatar_url", "")

        stmt = select(User).where(User.github_id == github_id)
        user = (await db.execute(stmt)).scalar_one_or_none()
        if not user:
            user = User(github_id=github_id, username=username, email=email, avatar_url=avatar)
            db.add(user)
            await db.flush()
        else:
            user.username = username
            if email:
                user.email = email
            if avatar:
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

    # 5. If installation_id is present, link GitHubInstallation and sync repositories
    if installation_id and org_id and user:
        try:
            inst_str = str(installation_id)
            inst_stmt = select(GitHubInstallation).where(GitHubInstallation.installation_id == inst_str)
            inst = (await db.execute(inst_stmt)).scalar_one_or_none()
            if not inst:
                inst = GitHubInstallation(
                    installation_id=inst_str,
                    organization_id=org_id,
                    account_login=user.username,
                    target_type="User",
                )
                db.add(inst)
            else:
                inst.organization_id = org_id
                inst.account_login = user.username
            await db.flush()

            # Sync repositories from GitHub for this installation
            repos = await sync_installation_repositories(inst_str)
            for r in repos:
                gh_repo_id = str(r["id"])
                r_stmt = select(Repository).where(Repository.github_repo_id == gh_repo_id)
                existing_repo = (await db.execute(r_stmt)).scalar_one_or_none()
                if not existing_repo:
                    db.add(
                        Repository(
                            organization_id=org_id,
                            github_repo_id=gh_repo_id,
                            full_name=r.get("full_name") or r.get("name", ""),
                            is_private=r.get("private", False),
                        )
                    )
        except Exception as e:
            logger.warning(f"Could not link installation or sync repos: {e}")

    # 6. Record login / install audit event
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    action_name = "auth.install" if installation_id else "auth.login"
    db.add(
        AuditEvent(
            user_id=user.id,
            organization_id=org_id,
            action=action_name,
            resource_type="session",
            resource_id=user.id,
            ip_address=client_ip,
            details_json=json.dumps({
                "provider": "github",
                "username": user.username,
                "email": user.email,
                "organization_id": org_id,
                "installation_id": installation_id,
                "setup_action": setup_action,
                "user_agent": user_agent,
            }),
        )
    )

    await db.commit()

    # 7. Create opaque session and redirect to dashboard
    base_app_url = settings.next_public_app_url.rstrip("/")
    target_url = f"{base_app_url}/dashboard?installed=true" if installation_id else f"{base_app_url}/dashboard"
    redirect_resp = RedirectResponse(target_url, status_code=status.HTTP_302_FOUND)
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

    # Check if GitHub App is installed for this organization
    inst_stmt = select(GitHubInstallation).where(GitHubInstallation.organization_id == org_id)
    has_install = (await db.execute(inst_stmt)).first() is not None

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
        is_installed=has_install,
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
async def get_me(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    inst_stmt = select(GitHubInstallation).where(GitHubInstallation.organization_id == tenant.organization.id)
    has_install = (await db.execute(inst_stmt)).first() is not None

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
        is_installed=has_install,
    )


@router.delete("/account", tags=["Current User"])
@router.post("/delete-account", tags=["Current User"])
async def delete_account(
    request: Request,
    response: Response,
    tenant: TenantContext = Depends(get_tenant_context),
    codesec_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete user account, uninstall GitHub App from user repos, and wipe all organization audit data."""
    user_id = tenant.user.id
    org_id = tenant.organization.id

    # 1. Uninstall GitHub App from user account and repositories
    inst_stmt = select(GitHubInstallation).where(GitHubInstallation.organization_id == org_id)
    installations = (await db.execute(inst_stmt)).scalars().all()
    for inst in installations:
        try:
            await uninstall_github_app(inst.installation_id)
        except Exception as e:
            logger.warning(f"Error calling GitHub uninstall for {inst.installation_id}: {e}")

    # 2. Delete all Findings associated with organization's Reviews
    review_ids_stmt = select(Review.id).where(Review.organization_id == org_id)
    review_ids = (await db.execute(review_ids_stmt)).scalars().all()
    if review_ids:
        await db.execute(delete(Finding).where(Finding.review_id.in_(review_ids)))

    # 3. Delete Reviews & ReviewJobs
    await db.execute(delete(Review).where(Review.organization_id == org_id))
    await db.execute(delete(ReviewJob).where(ReviewJob.organization_id == org_id))

    # 4. Delete Repositories & WebhookDeliveries
    repo_ids_stmt = select(Repository.id).where(Repository.organization_id == org_id)
    repo_ids = (await db.execute(repo_ids_stmt)).scalars().all()
    if repo_ids:
        await db.execute(delete(WebhookDelivery).where(WebhookDelivery.repository_id.in_(repo_ids)))
    await db.execute(delete(Repository).where(Repository.organization_id == org_id))

    # 5. Delete GitHub Installations
    await db.execute(delete(GitHubInstallation).where(GitHubInstallation.organization_id == org_id))

    # 6. Delete Audit & Usage Events
    await db.execute(
        delete(AuditEvent).where((AuditEvent.user_id == user_id) | (AuditEvent.organization_id == org_id))
    )
    await db.execute(delete(UsageEvent).where(UsageEvent.organization_id == org_id))

    # 7. Delete Memberships
    await db.execute(
        delete(Membership).where((Membership.user_id == user_id) | (Membership.organization_id == org_id))
    )

    # 8. Delete Organization
    await db.execute(delete(Organization).where(Organization.id == org_id))

    # 9. Delete User
    await db.execute(delete(User).where(User.id == user_id))

    await db.commit()

    # 10. Destroy Session in Redis and clear cookie
    await destroy_user_session(response, codesec_session)

    return {
        "status": "success",
        "message": "Account deleted, GitHub app uninstalled, and all security data wiped out cleanly.",
    }

