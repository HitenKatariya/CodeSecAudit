"""Backfill historical GitHub Pull Request security reviews into PostgreSQL."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit import AuditEvent
from app.db.models.github import GitHubInstallation, Repository
from app.db.models.review import Finding, Review, ReviewJob
from app.reviews.risk import calculate_risk_score, decide_verdict, filter_findings_by_policy, get_suggested_fix
from app.security.github_app import GITHUB_API_BASE, get_installation_token, sync_installation_repositories

logger = logging.getLogger("main_server")
_SEVERITY_WORD = re.compile(r"(CRITICAL|HIGH|MEDIUM|LOW)", re.IGNORECASE)
_CWE_RE = re.compile(r"CWE-\d+", re.IGNORECASE)


def _extract_payload_json(body: str) -> Optional[dict[str, Any]]:
    start, end = "CODESEC_AGENT_PAYLOAD_START", "CODESEC_AGENT_PAYLOAD_END"
    if start not in body or end not in body:
        return None
    try:
        data = json.loads(body.split(start, 1)[1].split(end, 1)[0].strip())
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _parse_markdown_findings(body: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line in body.splitlines():  # Executive Summary triage matrix rows
        if not line.strip().startswith("|") or "CWE-" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        sev_m = _SEVERITY_WORD.search(cells[0])
        cwe_m = _CWE_RE.search(cells[1])
        loc = cells[3].strip("` ")
        file_path, line_no = (loc.rsplit(":", 1)[0], loc.rsplit(":", 1)[1]) if ":" in loc else (loc, "0")
        cwe_id = cwe_m.group(0).upper() if cwe_m else "CWE-20"
        findings.append({
            "cwe_id": cwe_id,
            "severity": sev_m.group(1).lower() if sev_m else "medium",
            "title": (cells[4].replace("**", "").strip() or f"{cwe_id} Security Issue")[:255],
            "file_path": (file_path or "unknown")[:512],
            "line_number": int(line_no) if line_no.isdigit() else 0,
            "code_snippet": "",
            "suggested_fix": get_suggested_fix(cwe_id),
        })
    return findings


def _normalize_finding(raw: dict[str, Any]) -> dict[str, Any]:
    cwe = str(raw.get("cwe_id") or "CWE-20").upper()[:32]
    fix = raw.get("patch_suggested") or raw.get("suggested_fix") or raw.get("fix") or get_suggested_fix(cwe)
    try:
        line_no = int(raw.get("line_number") or raw.get("line") or 0)
    except (TypeError, ValueError):
        line_no = 0
    return {
        "cwe_id": cwe,
        "severity": str(raw.get("severity") or "medium").lower()[:32],
        "title": str(raw.get("title") or f"{cwe} Security Issue")[:255],
        "file_path": str(raw.get("file_path") or raw.get("file") or "unknown")[:512],
        "line_number": line_no,
        "code_snippet": str(raw.get("code_snippet") or raw.get("snippet") or "")[:300],
        "suggested_fix": str(fix)[:2000],
    }


def parse_bot_comment(body: str, fallback_sha: str) -> dict[str, Any]:
    """Normalize verdict, CVSS score, commit SHA, and findings from a CodeSecAudit PR comment."""
    sha_m = re.search(r"Target Commit:\*\*\s*`([0-9a-fA-F]+)`", body)
    commit_sha = sha_m.group(1) if sha_m else fallback_sha
    payload = _extract_payload_json(body)
    if payload is None:
        findings = _parse_markdown_findings(body)
        score_m = re.search(r"CVSS Security Risk Score:\*\*\s*`([0-9]+(?:\.[0-9]+)?)\s*/\s*10", body)
        risk_score = float(score_m.group(1)) if score_m else calculate_risk_score(findings)
        if "REQUEST CHANGES" in body:
            verdict = "REQUEST_CHANGES"
        elif "WARNING" in body:
            verdict = "WARNING"
        elif "APPROVE" in body:
            verdict = "APPROVE"
        else:
            verdict = decide_verdict(risk_score, findings=findings)
        return {"verdict": verdict, "risk_score": risk_score, "commit_sha": commit_sha, "findings": findings}

    findings = [_normalize_finding(f) for f in (payload.get("findings") or []) if isinstance(f, dict)]
    raw_score = payload.get("cvss_score")
    risk_score = float(raw_score) if raw_score is not None else calculate_risk_score(findings)
    return {
        "verdict": str(payload.get("verdict") or decide_verdict(risk_score, findings=findings)),
        "risk_score": risk_score,
        "commit_sha": commit_sha,
        "findings": findings,
    }


async def _gh_get(http: httpx.AsyncClient, path: str, headers: dict[str, str]) -> Any:
    resp = await http.get(f"{GITHUB_API_BASE}{path}", headers=headers)
    return resp.json() if resp.status_code == 200 else None


async def sync_repo_pr_reviews(
    db: AsyncSession,
    org_id: str,
    repo: Repository,
    installation_id: Optional[str] = None,
    github_token: Optional[str] = None,
    policy: Optional[dict[str, Any]] = None,
) -> dict[str, int]:
    """Fetch PRs + CodeSecAudit bot comments for repo and upsert missing reviews into PostgreSQL."""
    token = github_token
    if not token and installation_id:
        try:
            token = await get_installation_token(installation_id)
        except Exception as e:
            logger.warning(f"Install token unavailable for {repo.full_name}: {e}")

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    synced, skipped = 0, 0
    existing_rows = (await db.execute(select(Review).where(Review.repository_id == repo.id))).scalars().all()
    existing_by_pr_sha = {(r.pr_number, (r.commit_sha or "")[:12]): r for r in existing_rows}

    async with httpx.AsyncClient(timeout=20.0) as http:
        path = f"/repos/{repo.full_name}/pulls?state=all&per_page=50&sort=updated&direction=desc"
        prs = await _gh_get(http, path, headers)
        if not isinstance(prs, list):
            return {"synced": 0, "skipped": 0}

        for pr in prs:
            pr_num = int(pr.get("number") or 0)
            pr_title = str(pr.get("title") or f"PR #{pr_num}").strip()[:255]
            head_sha = str((pr.get("head") or {}).get("sha") or "HEAD")
            comments = await _gh_get(http, f"/repos/{repo.full_name}/issues/{pr_num}/comments?per_page=50", headers)
            bot_comments = [c for c in (comments or []) if "codesec" in str((c.get("user") or {}).get("login") or "").lower()]
            if not bot_comments:
                continue

            parsed = parse_bot_comment(bot_comments[-1].get("body") or "", head_sha)
            active_findings = filter_findings_by_policy(parsed["findings"], policy) if policy else parsed["findings"]
            verdict = decide_verdict(calculate_risk_score(active_findings), findings=active_findings, policy=policy) if policy else parsed["verdict"]
            short_sha = (parsed["commit_sha"] or head_sha)[:12]
            summary = f"{pr_title} — Found {len(active_findings)} issue(s). Risk score: {parsed['risk_score']}/10.0. Verdict: {verdict}." if active_findings else f"{pr_title} — No security issues detected."

            key = (pr_num, short_sha)
            if key in existing_by_pr_sha or (pr_num, head_sha[:12]) in existing_by_pr_sha:
                existing = existing_by_pr_sha.get(key) or existing_by_pr_sha.get((pr_num, head_sha[:12]))
                if existing and pr_title not in (existing.summary or ""):
                    existing.summary = summary
                skipped += 1
                continue

            created_raw = bot_comments[-1].get("created_at")
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00")) if created_raw else datetime.now(timezone.utc)
            job = ReviewJob(organization_id=org_id, repository_id=repo.id, pr_number=pr_num, commit_sha=parsed["commit_sha"], status="completed")
            db.add(job)
            await db.flush()
            rev = Review(
                organization_id=org_id, repository_id=repo.id, job_id=job.id, pr_number=pr_num,
                commit_sha=parsed["commit_sha"], risk_score=parsed["risk_score"], verdict=verdict,
                summary=summary, guidance_available=True, created_at=created_dt,
            )
            db.add(rev)
            await db.flush()
            for fin in active_findings:
                db.add(Finding(review_id=rev.id, organization_id=org_id, **fin))
            db.add(AuditEvent(
                organization_id=org_id, action="review_synced_from_github", resource_type="review",
                resource_id=rev.id,
                details_json=json.dumps({"pr_number": pr_num, "verdict": verdict, "commit_sha": short_sha}),
            ))
            existing_by_pr_sha[key] = rev
            synced += 1

    return {"synced": synced, "skipped": skipped}


async def sync_org_github_reviews(db: AsyncSession, org_id: str, github_token: Optional[str] = None) -> dict[str, Any]:
    """Discover repositories via org installations and sync all CodeSecAudit GitHub PR reviews."""
    # Historical verdicts are imported exactly as CodeSecAudit posted them on GitHub.
    # Tenant thresholds are applied dynamically by the Policies API when they change.
    insts = (await db.execute(select(GitHubInstallation).where(GitHubInstallation.organization_id == org_id))).scalars().all()
    install_id = insts[0].installation_id if insts else None
    for inst in insts:
        for r in await sync_installation_repositories(inst.installation_id):
            gh_id = str(r["id"])
            if not (await db.execute(select(Repository).where(Repository.github_repo_id == gh_id))).scalar_one_or_none():
                db.add(Repository(
                    organization_id=org_id, github_repo_id=gh_id,
                    full_name=r.get("full_name") or r.get("name", ""), is_private=r.get("private", False),
                ))
        await db.flush()

    repos = (await db.execute(select(Repository).where(Repository.organization_id == org_id))).scalars().all()
    total_synced, total_skipped = 0, 0
    for repo in repos:
        res = await sync_repo_pr_reviews(db, org_id, repo, installation_id=install_id, github_token=github_token)
        total_synced += res["synced"]
        total_skipped += res["skipped"]
    await db.commit()
    return {"synced": total_synced, "skipped": total_skipped, "repositories": len(repos)}
