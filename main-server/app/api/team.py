"""Organization team members and invitation lifecycle API endpoints."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    AcceptInvitationResponse,
    InviteMemberRequest,
    TeamInvitationResponse,
    TeamMemberResponse,
)
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.models.organization import Membership, OrganizationInvitation
from app.db.models.user import User
from app.db.session import get_db
from app.security.sessions import SESSION_COOKIE_NAME, get_current_user
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


@router.get("/invitations", response_model=list[TeamInvitationResponse])
async def list_team_invitations(
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """List pending invitations for the current organization."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    stmt = (
        select(OrganizationInvitation, User.username)
        .outerjoin(User, User.id == OrganizationInvitation.invited_by_user_id)
        .where(
            OrganizationInvitation.organization_id == tenant.organization.id,
            OrganizationInvitation.status == "pending",
        )
        .order_by(OrganizationInvitation.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    invitations: list[TeamInvitationResponse] = []
    expired_invitations = []

    for inv, inviter_username in rows:
        exp = inv.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            inv.status = "expired"
            expired_invitations.append(inv)
            continue

        invite_url = f"/invite/accept?token={inv.token}"
        invite_link = f"{settings.next_public_app_url}{invite_url}"

        invitations.append(
            TeamInvitationResponse(
                id=inv.id,
                organization_id=inv.organization_id,
                email=inv.email,
                role=inv.role,
                token=inv.token,
                invited_by=inviter_username or "Admin",
                invited_by_user_id=inv.invited_by_user_id,
                status=inv.status,
                expires_at=inv.expires_at.isoformat(),
                created_at=inv.created_at.isoformat(),
                invite_url=invite_url,
                invite_link=invite_link,
            )
        )

    if expired_invitations:
        await db.commit()

    return invitations


@router.post("/invite", response_model=TeamInvitationResponse)
async def invite_team_member(
    req: InviteMemberRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Generate a secure invitation token, store invitation, and return details with invite URL."""
    email_clean = req.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required",
        )

    role_clean = req.role.strip().lower().replace(" ", "_")
    valid_roles = {"admin", "security_lead", "developer", "viewer", "member"}
    if role_clean not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{req.role}'. Allowed roles: admin, security_lead, developer, viewer",
        )
    if role_clean == "member":
        role_clean = "developer"

    # Revoke any previous pending invitations for this email in this org
    prev_stmt = select(OrganizationInvitation).where(
        OrganizationInvitation.organization_id == tenant.organization.id,
        OrganizationInvitation.email == email_clean,
        OrganizationInvitation.status == "pending",
    )
    prev_invitations = (await db.execute(prev_stmt)).scalars().all()
    for prev in prev_invitations:
        prev.status = "revoked"

    settings = get_settings()
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    invitation = OrganizationInvitation(
        organization_id=tenant.organization.id,
        email=email_clean,
        role=role_clean,
        token=token,
        invited_by_user_id=tenant.user.id,
        status="pending",
        expires_at=expires_at,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    invite_url = f"/invite/accept?token={token}"
    invite_link = f"{settings.next_public_app_url}{invite_url}"

    return TeamInvitationResponse(
        id=invitation.id,
        organization_id=invitation.organization_id,
        email=invitation.email,
        role=invitation.role,
        token=invitation.token,
        invited_by=tenant.user.username if tenant.user else "Admin",
        invited_by_user_id=invitation.invited_by_user_id,
        status=invitation.status,
        expires_at=invitation.expires_at.isoformat(),
        created_at=invitation.created_at.isoformat(),
        invite_url=invite_url,
        invite_link=invite_link,
    )


@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Revoke/delete a pending invitation."""
    stmt = select(OrganizationInvitation).where(
        OrganizationInvitation.id == invitation_id,
        OrganizationInvitation.organization_id == tenant.organization.id,
    )
    invitation = (await db.execute(stmt)).scalar_one_or_none()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot revoke invitation with status '{invitation.status}'",
        )

    invitation.status = "revoked"
    await db.commit()

    return {"message": "Invitation revoked", "status": "revoked", "id": invitation_id}


@router.post("/invitations/{token}/accept", response_model=AcceptInvitationResponse)
async def accept_invitation(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    codesec_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    """Accept invitation with token for authenticated user and add them to Membership with the specified role."""
    stmt = select(OrganizationInvitation).where(OrganizationInvitation.token == token)
    invitation = (await db.execute(stmt)).scalar_one_or_none()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    now = datetime.now(timezone.utc)
    if invitation.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has been revoked",
        )
    if invitation.status == "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been accepted",
        )
    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation is {invitation.status}",
        )

    exp = invitation.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now:
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    # Check if membership already exists
    mem_stmt = select(Membership).where(
        Membership.organization_id == invitation.organization_id,
        Membership.user_id == user.id,
    )
    membership = (await db.execute(mem_stmt)).scalar_one_or_none()
    if membership:
        membership.role = invitation.role
    else:
        membership = Membership(
            organization_id=invitation.organization_id,
            user_id=user.id,
            role=invitation.role,
        )
        db.add(membership)

    invitation.status = "accepted"
    await db.commit()

    # Update active session organization in Redis if session exists
    if codesec_session:
        try:
            settings = get_settings()
            redis_service = get_redis_service(settings.redis_url)
            session_data = await redis_service.get_session(codesec_session)
            if session_data:
                session_data["organization_id"] = invitation.organization_id
                await redis_service.set_session(codesec_session, session_data, ttl_seconds=86400 * 7)
        except Exception:
            pass

    return AcceptInvitationResponse(
        message="Invitation accepted successfully",
        organization_id=invitation.organization_id,
        user_id=user.id,
        role=invitation.role,
        status="accepted",
    )
