"""CLI seed script to backfill all historical CodeSecAudit PR reviews from GitHub into Postgres."""

from __future__ import annotations

import argparse
import asyncio
import os
import httpx
from sqlalchemy import func, select
from app.db.models.github import Repository
from app.db.models.organization import Organization
from app.db.session import get_session_factory
from app.reviews.github_sync import GITHUB_API_BASE, sync_org_github_reviews, sync_repo_pr_reviews
from app.security.org_sync import resolve_org_for_github_account


async def _seed(repos: list[str], org_slug: str | None, token: str | None) -> None:
    factory = get_session_factory()
    async with factory() as db:
        if not repos:
            orgs = (await db.execute(select(Organization))).scalars().all()
            for org in orgs:
                res = await sync_org_github_reviews(db, org.id, github_token=token)
                print(f"Synced org={org.slug}: {res}")
            return

        for full_name in repos:
            owner = full_name.split("/")[0] if "/" in full_name else "default"
            if org_slug:
                org = (await db.execute(select(Organization).where(Organization.slug == org_slug))).scalar_one_or_none()
                if org is None:
                    org = Organization(name=f"{owner}'s Org", slug=org_slug)
                    db.add(org)
                    await db.flush()
            else:
                org = await resolve_org_for_github_account(db, owner)

            repo = (
                await db.execute(select(Repository).where(func.lower(Repository.full_name) == full_name.lower()))
            ).scalar_one_or_none()
            if repo is None:
                gh_id = full_name
                headers = {"Accept": "application/vnd.github+json"}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                async with httpx.AsyncClient(timeout=15.0) as http:
                    r = await http.get(f"{GITHUB_API_BASE}/repos/{full_name}", headers=headers)
                    if r.status_code == 200:
                        gh_id = str(r.json().get("id") or full_name)
                repo = Repository(organization_id=org.id, github_repo_id=gh_id, full_name=full_name, is_private=False)
                db.add(repo)
                await db.flush()

            res = await sync_repo_pr_reviews(db, org.id, repo, github_token=token)
            await db.commit()
            print(f"Seeded repo={full_name} org={org.slug}: {res}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed CodeSecAudit PR reviews from GitHub into Postgres.")
    parser.add_argument("--repo", action="append", default=[], help="GitHub owner/repo (repeatable)")
    parser.add_argument("--org-slug", default=None, help="Target Organization slug")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="Optional GitHub PAT for higher rate limits")
    args = parser.parse_args()
    asyncio.run(_seed(args.repo, args.org_slug, args.token))


if __name__ == "__main__":
    main()
