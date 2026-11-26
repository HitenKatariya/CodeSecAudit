"""Backfill historical GitHub Pull Request security reviews into PostgreSQL."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.redis import get_redis_service
from app.db.models.audit import AuditEvent
from app.db.models.github import GitHubInstallation, Repository
from app.db.models.organization import Membership, Organization
from app.db.models.review import Finding, Review, ReviewJob
from app.db.models.user import User
from app.reviews.comment_parser import parse_bot_comment
from app.security.github_app import (
    GITHUB_API_BASE,
    get_installation_token,
    list_app_installations,
    sync_installation_repositories,
)

logger = logging.getLogger("main_server")


async def _gh_get(http: httpx.AsyncClient, path: str, headers: dict[str, str]) -> Any:
    resp = await http.get(f"{GITHUB_API_BASE}{path}", headers=headers)
    return resp.json() if resp.status_code == 200 else None


async def _fetch_pr_bot_comments(repo_name: str, headers: dict[str, str]) -> list[tuple[dict, dict]]:
    async with httpx.AsyncClient(timeout=20.0) as http:
        prs = await _gh_get(http, f"/repos/{repo_name}/pulls?state=all&per_page=50&sort=updated&direction=desc", headers)
        if not isinstance(prs, list):
            return []
        sem = asyncio.Semaphore(6)

        async def _load(pr: dict) -> tuple[dict, Optional[dict]]:
            async with sem:
                comments = await _gh_get(http, f"/repos/{repo_name}/issues/{int(pr.get('number') or 0)}/comments?per_page=50", headers)
                bot = [c for c in (comments or []) if "codesec" in str((c.get("user") or {}).get("login") or "").lower()]
                return pr, (bot[-1] if bot else None)

        results = await asyncio.gather(*(_load(pr) for pr in prs))
        return [(pr, c) for pr, c in results if c is not None]


async def sync_repo_pr_reviews(
    db: AsyncSession,
    org_id: str,
    repo: Repository,
    installation_id: Optional[str] = None,
    github_token: Optional[str] = None,
) -> dict[str, int]:
    """Fetch PRs + CodeSecAudit bot comments for repo and upsert missing reviews into PostgreSQL."""
    token = github_token or os.getenv("GITHUB_TOKEN") or None
    if installation_id and not github_token:
        try:
            token = await get_installation_token(installation_id)
        except Exception as e:
            logger.warning(f"Install token unavailable for {repo.full_name}: {e}")

    headers = {"Accept": "application/vnd.github+json", **({"Authorization": f"Bearer {token}"} if token else {})}
    pr_comments = await _fetch_pr_bot_comments(repo.full_name, headers)
    if not pr_comments:
        return {"synced": 0, "skipped": 0}

    existing_rows = (await db.execute(select(Review).where(Review.repository_id == repo.id))).scalars().all()
    existing_by_pr_sha = {(r.pr_number, (r.commit_sha or "")[:12]): r for r in existing_rows}
    synced, skipped = 0, 0

    for pr, bot_comment in pr_comments:
        pr_num = int(pr.get("number") or 0)
        pr_title = str(pr.get("title") or f"PR #{pr_num}").strip()[:255]
        head_sha = str((pr.get("head") or {}).get("sha") or "HEAD")
        # Import exactly what CodeSecAudit posted on GitHub. Tenant thresholds are
        # applied dynamically by the Policies API when policy is saved, not here.
        parsed = parse_bot_comment(bot_comment.get("body") or "", head_sha)
        all_findings = parsed["findings"]
        risk_val = parsed["risk_score"]
        verdict = parsed["verdict"]
        short_sha = (parsed["commit_sha"] or head_sha)[:12]
        summary = f"{pr_title} — Found {len(all_findings)} issue(s). Risk score: {risk_val}/10.0. Verdict: {verdict}." if all_findings else f"{pr_title} — No security issues detected."

        existing = existing_by_pr_sha.get((pr_num, short_sha)) or existing_by_pr_sha.get((pr_num, head_sha[:12]))
        if existing:
            if pr_title not in (existing.summary or ""):
                existing.summary = summary
            skipped += 1
            continue

        created_raw = bot_comment.get("created_at")
        created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00")) if created_raw else datetime.now(timezone.utc)
        job = ReviewJob(organization_id=org_id, repository_id=repo.id, pr_number=pr_num, commit_sha=parsed["commit_sha"], status="completed")
        db.add(job)
        await db.flush()
        rev = Review(
            organization_id=org_id, repository_id=repo.id, job_id=job.id, pr_number=pr_num,
            commit_sha=parsed["commit_sha"], risk_score=risk_val, verdict=verdict,
            summary=summary, guidance_available=True, created_at=created_dt,
        )
        db.add(rev)
        await db.flush()
        for fin in all_findings:
            db.add(Finding(review_id=rev.id, organization_id=org_id, **fin))
        db.add(AuditEvent(
            organization_id=org_id, action="review_synced_from_github", resource_type="review",
            resource_id=rev.id, details_json=json.dumps({"pr_number": pr_num, "verdict": verdict, "commit_sha": short_sha}),
        ))
        existing_by_pr_sha[(pr_num, short_sha)] = rev
        synced += 1

    return {"synced": synced, "skipped": skipped}


async def discover_org_installations(db: AsyncSession, org_id: str, hint_logins: Optional[list[str]] = None) -> list[GitHubInstallation]:
    """Auto-link GitHub App installations whose account matches an org member (critical on fresh DBs)."""
    insts = (await db.execute(select(GitHubInstallation).where(GitHubInstallation.organization_id == org_id))).scalars().all()
    if insts:
        return list(insts)
    member_logins = {
        u.lower() for u in (await db.execute(select(User.username).join(Membership, Membership.user_id == User.id).where(Membership.organization_id == org_id))).scalars().all() if u
    }
    member_logins.update(h.strip().lower() for h in (hint_logins or []) if h)
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if org and org.slug:
        for suffix in ("-personal", "-org", "-workspace"):
            if org.slug.lower().endswith(suffix):
                member_logins.add(org.slug.lower()[:-len(suffix)])
    for item in await list_app_installations():
        acc = item.get("account") or {}
        login, inst_id = str(acc.get("login") or "").strip(), str(item.get("id") or "")
        if not login or not inst_id or (member_logins and login.lower() not in member_logins):
            continue
        existing = (await db.execute(select(GitHubInstallation).where(GitHubInstallation.installation_id == inst_id))).scalar_one_or_none()
        if existing is None:
            db.add(GitHubInstallation(installation_id=inst_id, organization_id=org_id, account_login=login, target_type=acc.get("type") or "User"))
            await db.flush()
    return list((await db.execute(select(GitHubInstallation).where(GitHubInstallation.organization_id == org_id))).scalars().all())


async def sync_org_github_reviews(db: AsyncSession, org_id: str, github_token: Optional[str] = None) -> dict[str, Any]:
    """Discover installations + repositories and sync all CodeSecAudit GitHub PR reviews."""
    insts = await discover_org_installations(db, org_id)
    repo_install_map: dict[str, str] = {}
    for inst in insts:
        for r in await sync_installation_repositories(inst.installation_id):
            gh_id = str(r["id"])
            repo_install_map[gh_id] = inst.installation_id
            if not (await db.execute(select(Repository).where(Repository.github_repo_id == gh_id))).scalar_one_or_none():
                db.add(Repository(organization_id=org_id, github_repo_id=gh_id, full_name=r.get("full_name") or r.get("name", ""), is_private=r.get("private", False)))
        await db.flush()

    repos = (await db.execute(select(Repository).where(Repository.organization_id == org_id))).scalars().all()
    fallback_inst = insts[0].installation_id if insts else None
    total_synced, total_skipped = 0, 0
    for repo in repos:
        res = await sync_repo_pr_reviews(db, org_id, repo, installation_id=repo_install_map.get(repo.github_repo_id, fallback_inst), github_token=github_token)
        total_synced += res["synced"]
        total_skipped += res["skipped"]
    await db.commit()
    return {"synced": total_synced, "skipped": total_skipped, "repositories": len(repos)}


async def ensure_org_history_synced(db: AsyncSession, org_id: str) -> None:
    """Trigger one-time Redis-locked GitHub history backfill when an org has not synced yet."""
    try:
        redis = await get_redis_service(get_settings().redis_url).get_async()
        sync_key, lock_key = f"gh_history_synced_v3:{org_id}", f"gh_history_sync_lock:{org_id}"
        if await redis.get(sync_key):
            return
        if not await redis.set(lock_key, "1", nx=True, ex=60):
            return
        try:
            res = await sync_org_github_reviews(db, org_id)
            await redis.setex(sync_key, 3600 if res.get("repositories", 0) > 0 else 120, "1")
        finally:
            await redis.delete(lock_key)
    except Exception as e:
        logger.warning(f"GitHub history backfill skipped for org {org_id}: {e}")
        await db.rollback()
