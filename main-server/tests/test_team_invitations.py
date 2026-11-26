"""Comprehensive tests for Team Member Invitation lifecycle."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.organization import Membership, Organization, OrganizationInvitation
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.security.sessions import get_current_user
from app.security.tenant import TenantContext, get_tenant_context


@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def setup_data(async_db: AsyncSession):
    # Create test organizations
    org1 = Organization(
        id=str(uuid.uuid4()),
        name="Acme Corp",
        slug="acme-corp",
        plan="enterprise",
        monthly_pr_quota=100,
    )
    org2 = Organization(
        id=str(uuid.uuid4()),
        name="Beta Inc",
        slug="beta-inc",
        plan="free",
        monthly_pr_quota=30,
    )
    async_db.add_all([org1, org2])

    # Create admin user
    admin_user = User(
        id=str(uuid.uuid4()),
        github_id="1001",
        username="admin_alice",
        email="alice@acme.com",
        is_admin=True,
    )
    # Create invitee user
    invitee_user = User(
        id=str(uuid.uuid4()),
        github_id="2002",
        username="bob_dev",
        email="bob@example.com",
        is_admin=False,
    )
    # Create other org user
    other_user = User(
        id=str(uuid.uuid4()),
        github_id="3003",
        username="charlie_beta",
        email="charlie@beta.com",
        is_admin=False,
    )
    async_db.add_all([admin_user, invitee_user, other_user])

    # Create membership for admin in org1
    admin_membership = Membership(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        user_id=admin_user.id,
        role="admin",
    )
    async_db.add(admin_membership)

    await async_db.commit()

    return {
        "org1": org1,
        "org2": org2,
        "admin_user": admin_user,
        "invitee_user": invitee_user,
        "other_user": other_user,
    }


@pytest.mark.asyncio
async def test_invite_team_member_success(async_db: AsyncSession, setup_data: dict):
    org1 = setup_data["org1"]
    admin_user = setup_data["admin_user"]

    async def override_get_db():
        yield async_db

    async def override_get_tenant_context():
        return TenantContext(user=admin_user, organization=org1, role="admin")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_context] = override_get_tenant_context

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/team/invite",
                json={"email": "developer@example.com", "role": "security_lead"},
            )
            assert resp.status_code == 200
            data = resp.json()

            assert data["email"] == "developer@example.com"
            assert data["role"] == "security_lead"
            assert data["status"] == "pending"
            assert data["organization_id"] == org1.id
            assert data["invited_by"] == "admin_alice"
            assert data["invited_by_user_id"] == admin_user.id
            assert "token" in data
            assert len(data["token"]) >= 32
            assert "/invite/accept?token=" in data["invite_url"]
            assert data["invite_url"] in data["invite_link"]

            # Verify in DB
            stmt = select(OrganizationInvitation).where(OrganizationInvitation.id == data["id"])
            db_inv = (await async_db.execute(stmt)).scalar_one_or_none()
            assert db_inv is not None
            assert db_inv.email == "developer@example.com"
            assert db_inv.role == "security_lead"
            assert db_inv.status == "pending"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_invite_validation_errors(async_db: AsyncSession, setup_data: dict):
    org1 = setup_data["org1"]
    admin_user = setup_data["admin_user"]

    async def override_get_db():
        yield async_db

    async def override_get_tenant_context():
        return TenantContext(user=admin_user, organization=org1, role="admin")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_context] = override_get_tenant_context

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Invalid email
            resp = await client.post(
                "/v1/team/invite",
                json={"email": "not-an-email", "role": "developer"},
            )
            assert resp.status_code == 400
            assert "email" in resp.json()["detail"].lower()

            # Invalid role
            resp = await client.post(
                "/v1/team/invite",
                json={"email": "valid@example.com", "role": "super_god"},
            )
            assert resp.status_code == 400
            assert "role" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_team_invitations(async_db: AsyncSession, setup_data: dict):
    org1 = setup_data["org1"]
    org2 = setup_data["org2"]
    admin_user = setup_data["admin_user"]

    # Create pending invitation in org1
    inv1 = OrganizationInvitation(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        email="pending1@example.com",
        role="developer",
        token="token_12345678901234567890123456789012",
        invited_by_user_id=admin_user.id,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    # Create already revoked invitation in org1 (should not appear in pending list)
    inv2 = OrganizationInvitation(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        email="revoked@example.com",
        role="developer",
        token="token_revoked",
        invited_by_user_id=admin_user.id,
        status="revoked",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    # Create invitation in org2 (tenant isolation: should not appear in org1 list)
    inv3 = OrganizationInvitation(
        id=str(uuid.uuid4()),
        organization_id=org2.id,
        email="org2_pending@example.com",
        role="developer",
        token="token_org2",
        invited_by_user_id=admin_user.id,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    async_db.add_all([inv1, inv2, inv3])
    await async_db.commit()

    async def override_get_db():
        yield async_db

    async def override_get_tenant_context():
        return TenantContext(user=admin_user, organization=org1, role="admin")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_context] = override_get_tenant_context

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/team/invitations")
            assert resp.status_code == 200
            invs = resp.json()

            assert len(invs) == 1
            assert invs[0]["email"] == "pending1@example.com"
            assert invs[0]["status"] == "pending"
            assert invs[0]["organization_id"] == org1.id
            assert invs[0]["invited_by"] == "admin_alice"
            assert "/invite/accept?token=" in invs[0]["invite_url"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_revoke_invitation(async_db: AsyncSession, setup_data: dict):
    org1 = setup_data["org1"]
    org2 = setup_data["org2"]
    admin_user = setup_data["admin_user"]

    inv = OrganizationInvitation(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        email="torevoke@example.com",
        role="developer",
        token="token_to_revoke",
        invited_by_user_id=admin_user.id,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    async_db.add(inv)
    await async_db.commit()

    async def override_get_db():
        yield async_db

    async def override_get_tenant_context():
        return TenantContext(user=admin_user, organization=org1, role="admin")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_context] = override_get_tenant_context

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Revoke successfully
            resp = await client.delete(f"/v1/team/invitations/{inv.id}")
            assert resp.status_code == 200
            assert resp.json()["status"] == "revoked"

            # Check in DB
            stmt = select(OrganizationInvitation).where(OrganizationInvitation.id == inv.id)
            db_inv = (await async_db.execute(stmt)).scalar_one_or_none()
            assert db_inv.status == "revoked"

            # Cannot revoke already revoked invitation
            resp_again = await client.delete(f"/v1/team/invitations/{inv.id}")
            assert resp_again.status_code == 400

            # Cannot revoke non-existent invitation
            resp_404 = await client.delete(f"/v1/team/invitations/{uuid.uuid4()}")
            assert resp_404.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_accept_invitation_success(async_db: AsyncSession, setup_data: dict):
    org1 = setup_data["org1"]
    admin_user = setup_data["admin_user"]
    invitee_user = setup_data["invitee_user"]

    token = "test_secure_invite_token_12345678"
    inv = OrganizationInvitation(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        email=invitee_user.email,
        role="viewer",
        token=token,
        invited_by_user_id=admin_user.id,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    async_db.add(inv)
    await async_db.commit()

    async def override_get_db():
        yield async_db

    async def override_get_current_user():
        return invitee_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/v1/team/invitations/{token}/accept")
            assert resp.status_code == 200
            data = resp.json()

            assert data["status"] == "accepted"
            assert data["organization_id"] == org1.id
            assert data["user_id"] == invitee_user.id
            assert data["role"] == "viewer"

            # Verify in DB: invitation status is accepted
            stmt_inv = select(OrganizationInvitation).where(OrganizationInvitation.id == inv.id)
            updated_inv = (await async_db.execute(stmt_inv)).scalar_one()
            assert updated_inv.status == "accepted"

            # Verify in DB: Membership created for user
            stmt_mem = select(Membership).where(
                Membership.organization_id == org1.id,
                Membership.user_id == invitee_user.id,
            )
            membership = (await async_db.execute(stmt_mem)).scalar_one_or_none()
            assert membership is not None
            assert membership.role == "viewer"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_accept_invitation_errors(async_db: AsyncSession, setup_data: dict):
    org1 = setup_data["org1"]
    admin_user = setup_data["admin_user"]
    invitee_user = setup_data["invitee_user"]

    # 1. Expired invitation
    expired_token = "expired_token_12345"
    inv_expired = OrganizationInvitation(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        email="expired@example.com",
        role="developer",
        token=expired_token,
        invited_by_user_id=admin_user.id,
        status="pending",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    # 2. Revoked invitation
    revoked_token = "revoked_token_12345"
    inv_revoked = OrganizationInvitation(
        id=str(uuid.uuid4()),
        organization_id=org1.id,
        email="revoked@example.com",
        role="developer",
        token=revoked_token,
        invited_by_user_id=admin_user.id,
        status="revoked",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    async_db.add_all([inv_expired, inv_revoked])
    await async_db.commit()

    async def override_get_db():
        yield async_db

    async def override_get_current_user():
        return invitee_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Non-existent token -> 404
            resp_404 = await client.post("/v1/team/invitations/non_existent_token/accept")
            assert resp_404.status_code == 404

            # 2. Expired invitation -> 400
            resp_expired = await client.post(f"/v1/team/invitations/{expired_token}/accept")
            assert resp_expired.status_code == 400
            assert "expired" in resp_expired.json()["detail"].lower()

            # 3. Revoked invitation -> 400
            resp_revoked = await client.post(f"/v1/team/invitations/{revoked_token}/accept")
            assert resp_revoked.status_code == 400
            assert "revoked" in resp_revoked.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
