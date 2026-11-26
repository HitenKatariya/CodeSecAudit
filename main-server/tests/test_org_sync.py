"""Tests for organization resolution and orphan webhook-data reconciliation."""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.github import GitHubInstallation, Repository
from app.db.models.organization import Membership, Organization
from app.db.models.review import Finding, Review, ReviewJob
from app.db.models.user import User
from app.security.org_sync import reconcile_user_organization, resolve_org_for_github_account


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_webhook_and_login_share_same_organization(db_session):
    webhook_org = await resolve_org_for_github_account(db_session, "OMCHOKSI108")
    assert webhook_org.slug == "omchoksi108-personal"

    # Simulated OAuth login later calls resolve_org_for_github_account
    login_org = await resolve_org_for_github_account(db_session, "OMCHOKSI108")
    assert login_org.id == webhook_org.id


async def test_other_tenant_not_claimed_across_accounts(db_session):
    om_user = User(id=str(uuid.uuid4()), github_id="gh_1", username="OMCHOKSI108", email="om@test.dev")
    om_org = Organization(id=str(uuid.uuid4()), name="OMCHOKSI108's Org", slug="omchoksi108-personal")
    db_session.add_all([om_user, om_org, Membership(organization_id=om_org.id, user_id=om_user.id, role="admin")])
    await db_session.commit()

    # HitenKatariya webhook arrives before HitenKatariya logs in: must create its own org, NOT pick OM's org
    hiten_org = await resolve_org_for_github_account(db_session, "HitenKatariya")
    assert hiten_org.id != om_org.id
    assert hiten_org.slug == "hitenkatariya-personal"


async def test_reconcile_moves_orphan_webhook_reviews_into_active_org(db_session):
    user = User(id=str(uuid.uuid4()), github_id="gh_om", username="OMCHOKSI108", email="om@test.dev")
    active_org = Organization(id=str(uuid.uuid4()), name="OMCHOKSI108's Org", slug="omchoksi108-personal")
    orphan_org = Organization(id=str(uuid.uuid4()), name="OMCHOKSI108's Org", slug="omchoksi108-org")
    db_session.add_all([
        user,
        active_org,
        orphan_org,
        Membership(organization_id=active_org.id, user_id=user.id, role="admin"),
    ])
    await db_session.flush()

    inst = GitHubInstallation(
        installation_id="inst-om-1",
        organization_id=orphan_org.id,
        account_login="OMCHOKSI108",
        target_type="User",
    )
    repo = Repository(
        organization_id=orphan_org.id,
        github_repo_id="repo-om-1",
        full_name="OMCHOKSI108/CodeSecurityAuditAgent",
        is_private=False,
    )
    db_session.add_all([inst, repo])
    await db_session.flush()

    job = ReviewJob(
        organization_id=orphan_org.id,
        repository_id=repo.id,
        pr_number=19,
        commit_sha="7dc86d6",
        status="completed",
    )
    db_session.add(job)
    await db_session.flush()

    rev = Review(
        organization_id=orphan_org.id,
        repository_id=repo.id,
        job_id=job.id,
        pr_number=19,
        commit_sha="7dc86d6",
        risk_score=0.0,
        verdict="APPROVE",
        summary="No security issues detected.",
    )
    db_session.add(rev)
    await db_session.flush()

    finding = Finding(
        review_id=rev.id,
        organization_id=orphan_org.id,
        cwe_id="CWE-352",
        severity="medium",
        title="Sample",
        file_path="a.py",
        line_number=1,
    )
    db_session.add(finding)
    await db_session.commit()

    merged = await reconcile_user_organization(db_session, user, active_org.id)
    await db_session.commit()

    assert merged == 1
    assert (await db_session.execute(select(Review).where(Review.organization_id == active_org.id))).scalar_one().pr_number == 19
    assert (await db_session.execute(select(Repository).where(Repository.organization_id == active_org.id))).scalar_one().full_name == "OMCHOKSI108/CodeSecurityAuditAgent"
    assert (await db_session.execute(select(Organization).where(Organization.id == orphan_org.id))).scalar_one_or_none() is None
