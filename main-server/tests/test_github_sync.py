"""Tests for backfilling CodeSecAudit PR review comments into the database."""

import json

from app.reviews.github_sync import parse_bot_comment


def _payload_comment(verdict: str, cvss: float, findings: list[dict]) -> str:
    payload = {"schema_version": "1.0", "verdict": verdict, "cvss_score": cvss, "findings": findings}
    return (
        "## CodeSecAudit AI — Security Audit Report\n"
        "> **Verdict:** **REQUEST CHANGES** | **CVSS Security Risk Score:** "
        f"`{cvss} / 10.0` | **Target Commit:** `abc123def4567890`\n"
        "CODESEC_AGENT_PAYLOAD_START\n"
        + json.dumps(payload)
        + "\nCODESEC_AGENT_PAYLOAD_END\n"
    )


def test_parse_payload_comment_normalizes_findings() -> None:
    body = _payload_comment("WARNING", 6.5, [{
        "cwe_id": "cwe-352",
        "severity": "MEDIUM",
        "title": "CSRF Protection Disabled",
        "file_path": "app/services/live_audit_medium.py",
        "line_number": "10",
        "code_snippet": "@csrf_exempt",
        "patch_suggested": "Enforce CSRF tokens and SameSite cookies",
    }])
    result = parse_bot_comment(body, "fallbacksha")
    assert result["verdict"] == "WARNING"
    assert result["risk_score"] == 6.5
    assert result["commit_sha"] == "abc123def4567890"
    finding = result["findings"][0]
    assert finding["cwe_id"] == "CWE-352"
    assert finding["severity"] == "medium"
    assert finding["line_number"] == 10
    assert finding["suggested_fix"] == "Enforce CSRF tokens and SameSite cookies"


def test_parse_markdown_comment_without_payload() -> None:
    body = (
        "> **Verdict:** 🛑 **REQUEST CHANGES** | **CVSS Security Risk Score:** `9.89 / 10.0` "
        "| **Target Commit:** `deadbeefcafe1234`\n"
        "| Severity | CWE ID | Category | Location | Vulnerability Title | Action |\n"
        "|:---:|:---:|:---:|:---:|:---:|:---:|\n"
        "| 🔴 `CRITICAL` | [`CWE-89`](https://cwe.mitre.org/data/definitions/89.html) | A03 | "
        "`app/db.py:42` | **SQL Injection via String Concatenation** | Fix Required |\n"
    )
    result = parse_bot_comment(body, "fallbacksha")
    assert result["verdict"] == "REQUEST_CHANGES"
    assert result["risk_score"] == 9.89
    assert result["commit_sha"] == "deadbeefcafe1234"
    assert result["findings"][0]["file_path"] == "app/db.py"
    assert result["findings"][0]["line_number"] == 42


def test_parse_comment_falls_back_to_head_sha() -> None:
    result = parse_bot_comment("No structured payload here", "0123456789abcdef")
    assert result["commit_sha"] == "0123456789abcdef"
    assert result["verdict"] == "APPROVE"


def test_import_keeps_github_verdict_even_with_strict_org_policy() -> None:
    """Historical imports must match the bot comment; policies apply on save, not import."""
    import asyncio
    import uuid
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    import app.reviews.github_sync as gh_sync
    from app.db.base import Base
    from app.db.models.github import Repository
    from app.db.models.organization import Organization
    from app.db.models.review import Review

    body = _payload_comment("WARNING", 6.5, [{
        "cwe_id": "CWE-352", "severity": "medium", "title": "CSRF Protection Disabled",
        "file_path": "app/api.py", "line_number": 10, "code_snippet": "@csrf_exempt",
    }])

    async def fake_fetch(repo_name, headers):
        return [(
            {"number": 20, "title": "feat: notification preferences", "head": {"sha": "abc123def456"}},
            {"user": {"login": "codesecurityaudit-app"}, "body": body, "created_at": "2026-11-26T18:00:00Z"},
        )]

    original = gh_sync._fetch_pr_bot_comments
    gh_sync._fetch_pr_bot_comments = fake_fetch

    async def run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with factory() as db:
            org = Organization(id=str(uuid.uuid4()), name="Strict Org", slug="strict-org", policy_json='{"block_medium": true, "min_security_score": 80}')
            repo = Repository(id=str(uuid.uuid4()), organization_id=org.id, github_repo_id="r2", full_name="acme/app", is_private=False)
            db.add_all([org, repo])
            await db.commit()
            await gh_sync.sync_repo_pr_reviews(db, org.id, repo)
            rev = (await db.execute(select(Review).where(Review.repository_id == repo.id))).scalar_one()
            assert rev.verdict == "WARNING"
            assert rev.risk_score == 6.5
        await engine.dispose()

    try:
        asyncio.run(run())
    finally:
        gh_sync._fetch_pr_bot_comments = original


def test_parse_markdown_verdict_header_ignores_body_words() -> None:
    body = (
        "> **Verdict:** ✅ **APPROVE** | **CVSS Security Risk Score:** `0.00 / 10.0` "
        "| **Target Commit:** `abc1234`\n\n"
        "Note: Avoid WARNING triggers or REQUEST CHANGES by sanitizing input."
    )
    result = parse_bot_comment(body, "abc1234")
    assert result["verdict"] == "APPROVE"


async def test_sync_repo_pr_reviews_persists_findings_with_confidence(monkeypatch) -> None:
    import uuid
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    import app.reviews.github_sync as gh_sync
    from app.db.base import Base
    from app.db.models.github import Repository
    from app.db.models.organization import Organization
    from app.db.models.review import Finding, Review

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    body = _payload_comment("REQUEST_CHANGES", 9.4, [{
        "cwe_id": "CWE-89",
        "severity": "critical",
        "title": "SQL Injection",
        "file_path": "app/bad.py",
        "line_number": 12,
        "confidence": 0.96,
    }])

    async def fake_fetch(repo_name, headers):
        return [(
            {"number": 21, "title": "feat: severe vuln PR", "head": {"sha": "deadbeef1234"}},
            {"user": {"login": "codesecaudit-ai[bot]"}, "body": body, "created_at": "2026-11-26T18:00:00Z"},
        )]

    monkeypatch.setattr(gh_sync, "_fetch_pr_bot_comments", fake_fetch)

    async with factory() as db:
        org = Organization(id=str(uuid.uuid4()), name="Test Org", slug="test-org")
        repo = Repository(id=str(uuid.uuid4()), organization_id=org.id, github_repo_id="r1", full_name="OMCHOKSI108/CodeSecurityAuditAgent", is_private=False)
        db.add_all([org, repo])
        await db.commit()

        res = await gh_sync.sync_repo_pr_reviews(db, org.id, repo)
        await db.commit()
        assert res == {"synced": 1, "skipped": 0, "repaired": 0}

        rev = (await db.execute(select(Review).where(Review.repository_id == repo.id))).scalar_one()
        assert rev.verdict == "REQUEST_CHANGES"
        assert "feat: severe vuln PR" in rev.summary
        fin = (await db.execute(select(Finding).where(Finding.review_id == rev.id))).scalar_one()
        assert fin.cwe_id == "CWE-89"

        # A stale verdict from an older import is repaired on the next sync.
        rev.verdict = "WARNING"
        await db.commit()
        res = await gh_sync.sync_repo_pr_reviews(db, org.id, repo)
        await db.commit()
        assert res == {"synced": 0, "skipped": 0, "repaired": 1}
        assert (await db.execute(select(Review).where(Review.id == rev.id))).scalar_one().verdict == "REQUEST_CHANGES"

    await engine.dispose()


async def test_sync_repo_pr_reviews_without_bot_comments_returns_full_counts(monkeypatch) -> None:
    """Repos with no bot comments must not break the org-level aggregator."""
    import uuid
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    import app.reviews.github_sync as gh_sync
    from app.db.base import Base
    from app.db.models.github import Repository
    from app.db.models.organization import Organization

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async def no_comments(*_):
        return []

    monkeypatch.setattr(gh_sync, "_fetch_pr_bot_comments", no_comments)

    async with factory() as db:
        org = Organization(id=str(uuid.uuid4()), name="Test Org", slug="test-org")
        repo = Repository(id=str(uuid.uuid4()), organization_id=org.id, github_repo_id="r2", full_name="empty/repo", is_private=False)
        db.add_all([org, repo])
        await db.commit()
        assert await gh_sync.sync_repo_pr_reviews(db, org.id, repo) == {"synced": 0, "skipped": 0, "repaired": 0}

    await engine.dispose()

