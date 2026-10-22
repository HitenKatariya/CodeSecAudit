"""Database and Redis seeder for CodeSecAudit AI testing and demo."""

import asyncio
import json
from datetime import datetime, timezone
import redis.asyncio as aioredis
from sqlalchemy import select
from app.core.config import get_settings
from app.db.models.github import GitHubInstallation, Repository
from app.db.models.organization import Membership, Organization
from app.db.models.review import Finding, Review, ReviewJob
from app.db.models.user import User
from app.db.session import get_session_factory

TEST_SESSION_ID = "test-session-admin"
ORG_ID = "org-acme"
USER_ID = "usr-admin"
REPO_ID = "repo-1"
GH_INSTALL_ID = "12345678"
GH_REPO_ID = "98765432"

async def seed_data():
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as db:
        user = (await db.execute(select(User).where(User.id == USER_ID))).scalar_one_or_none()
        if not user:
            user = User(
                id=USER_ID,
                github_id="108",
                username="omchoksi",
                email="om@codesec.ai",
                avatar_url="https://avatars.githubusercontent.com/u/108?v=4",
                is_admin=True,
            )
            db.add(user)

        org = (await db.execute(select(Organization).where(Organization.id == ORG_ID))).scalar_one_or_none()
        if not org:
            org = Organization(id=ORG_ID, name="Acme Engineering", slug="acme-engineering")
            db.add(org)
            await db.flush()

        mem = (await db.execute(select(Membership).where(Membership.user_id == USER_ID, Membership.organization_id == ORG_ID))).scalar_one_or_none()
        if not mem:
            db.add(Membership(organization_id=ORG_ID, user_id=USER_ID, role="admin"))

        inst = (await db.execute(select(GitHubInstallation).where(GitHubInstallation.installation_id == GH_INSTALL_ID))).scalar_one_or_none()
        if not inst:
            db.add(GitHubInstallation(
                installation_id=GH_INSTALL_ID,
                organization_id=ORG_ID,
                account_login="omchoksi",
                target_type="User",
            ))

        repo = (await db.execute(select(Repository).where(Repository.id == REPO_ID))).scalar_one_or_none()
        if not repo:
            repo = Repository(
                id=REPO_ID,
                organization_id=ORG_ID,
                github_repo_id=GH_REPO_ID,
                full_name="omchoksi/CodeSecurityAuditAgent",
                is_private=False,
            )
            db.add(repo)
            await db.flush()

        # Seed initial review with findings if none exists
        rev = (await db.execute(select(Review).where(Review.organization_id == ORG_ID))).scalars().first()
        if not rev:
            review = Review(
                id="rev-demo-101",
                organization_id=ORG_ID,
                repository_id=REPO_ID,
                pr_number=42,
                commit_sha="a1b2c3d4e5f67890",
                risk_score=78,
                verdict="REQUEST_CHANGES",
                summary="Detected 2 critical vulnerabilities (SQL Injection, Command Injection). Changes requested.",
                guidance_available=True,
            )
            db.add(review)
            await db.flush()

            db.add(Finding(
                review_id=review.id,
                organization_id=ORG_ID,
                cwe_id="CWE-89",
                severity="critical",
                title="SQL Injection in user parameter",
                file_path="server/routes/auth.py",
                line_number=45,
                code_snippet='db.execute(f"SELECT * FROM users WHERE username = \'{user_input}\'")',
                suggested_fix="Use parameterized queries with prepared statements.",
            ))
            db.add(Finding(
                review_id=review.id,
                organization_id=ORG_ID,
                cwe_id="CWE-78",
                severity="high",
                title="OS Command Injection via os.system()",
                file_path="server/utils/export.py",
                line_number=88,
                code_snippet='os.system("tar -czf backup.tar.gz " + user_filename)',
                suggested_fix="Sanitize arguments and use subprocess.run with arguments array.",
            ))

        await db.commit()
        print("✅ Database seeding complete.")

    # Seed Redis session and sample stream logs
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    session_data = {"user_id": USER_ID, "organization_id": ORG_ID}
    await redis_client.setex(f"session:{TEST_SESSION_ID}", 86400 * 30, json.dumps(session_data))

    now = datetime.now(timezone.utc).isoformat()
    for srv in ["main-server", "client", "rag-server"]:
        stream_key = f"log:{srv}"
        await redis_client.xadd(stream_key, {
            "timestamp": now,
            "level": "INFO",
            "message": f"Service {srv} initialized and listening on container port",
            "logger": f"{srv}.core",
            "service": srv,
        })
    await redis_client.close()
    print("✅ Redis session and log streams seeded.")

if __name__ == "__main__":
    asyncio.run(seed_data())
