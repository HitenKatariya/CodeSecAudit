"""Organization resolution and orphan webhook-data reconciliation helpers."""

import logging
import secrets
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit import AuditEvent, UsageEvent
from app.db.models.github import GitHubInstallation, Repository
from app.db.models.organization import Membership, Organization, OrganizationInvitation
from app.db.models.review import Finding, Review, ReviewJob
from app.db.models.user import User

logger = logging.getLogger("main_server")


async def find_member_org_for_username(db: AsyncSession, username: str) -> Organization | None:
    """Return the active Organization belonging to a User whose username matches (case-insensitive)."""
    clean = (username or "").strip().lower()
    if not clean:
        return None
    stmt = (
        select(Organization)
        .join(Membership, Membership.organization_id == Organization.id)
        .join(User, User.id == Membership.user_id)
        .where(func.lower(User.username) == clean)
        .order_by(Membership.created_at.asc())
    )
    return (await db.execute(stmt)).scalars().first()


async def resolve_org_for_github_account(db: AsyncSession, account_login: str) -> Organization:
    """Resolve an Organization for a GitHub login without mixing across unrelated tenants."""
    clean = (account_login or "").strip()
    lower = clean.lower()

    if lower:
        member_org = await find_member_org_for_username(db, clean)
        if member_org is not None:
            return member_org

        # Prefer -personal over -org if an un-membered org already exists for this GitHub user
        for candidate_slug in (f"{lower}-personal", f"{lower}-org"):
            org = (await db.execute(select(Organization).where(Organization.slug == candidate_slug))).scalar_one_or_none()
            if org is not None:
                return org

    base_slug = f"{(lower or 'default').replace(' ', '-')}-personal"
    slug = base_slug
    if (await db.execute(select(Organization.id).where(Organization.slug == slug))).scalar_one_or_none():
        slug = f"{base_slug}-{secrets.token_hex(3)}"

    org = Organization(name=f"{clean or 'Default'}'s Org", slug=slug)
    db.add(org)
    await db.flush()
    return org


async def _is_orphan_org(db: AsyncSession, org_id: str) -> bool:
    has_member = (await db.execute(select(Membership.id).where(Membership.organization_id == org_id).limit(1))).first()
    return has_member is None


async def reconcile_user_organization(db: AsyncSession, user: User, active_org_id: str) -> int:
    """Claim un-membered webhook-created installations/repos/reviews matching user.username into active_org_id."""
    username = (getattr(user, "username", None) or "").strip()
    if not username or not active_org_id:
        return 0
    lower_user = username.lower()

    candidate_ids: set[str] = set()
    inst_rows = (
        await db.execute(
            select(GitHubInstallation.organization_id).where(
                func.lower(GitHubInstallation.account_login) == lower_user,
                GitHubInstallation.organization_id != active_org_id,
            )
        )
    ).scalars().all()
    candidate_ids.update(inst_rows)

    repo_rows = (
        await db.execute(
            select(Repository.organization_id).where(
                Repository.full_name.ilike(f"{username}/%"),
                Repository.organization_id != active_org_id,
            )
        )
    ).scalars().all()
    candidate_ids.update(repo_rows)

    slug_rows = (
        await db.execute(
            select(Organization.id).where(
                Organization.slug.in_([f"{lower_user}-org", f"{lower_user}-personal"]),
                Organization.id != active_org_id,
            )
        )
    ).scalars().all()
    candidate_ids.update(slug_rows)

    merged = 0
    for orphan_org_id in candidate_ids:
        if not await _is_orphan_org(db, orphan_org_id):
            continue
        for model in (GitHubInstallation, Repository, ReviewJob, Review, Finding, UsageEvent, AuditEvent):
            await db.execute(
                update(model).where(model.organization_id == orphan_org_id).values(organization_id=active_org_id)
            )
        await db.execute(delete(OrganizationInvitation).where(OrganizationInvitation.organization_id == orphan_org_id))
        await db.execute(delete(Organization).where(Organization.id == orphan_org_id))
        merged += 1
        logger.info(f"Reconciled orphan org {orphan_org_id} for user {username} into org {active_org_id}")

    return merged
