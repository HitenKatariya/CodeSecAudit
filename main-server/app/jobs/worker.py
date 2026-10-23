"""Background review job processor worker."""

import asyncio
import logging
from sqlalchemy import select
from app.core.config import get_settings
from app.core.logging import setup_logger
from app.db.models.audit import AuditEvent
from app.db.models.review import Finding, Review, ReviewJob
from app.db.session import get_session_factory
from app.jobs.queue import dequeue_review_job
from app.reviews.diff_parser import extract_added_lines, split_diff_by_file
from app.reviews.engine import scan_diff_lines, scan_source_code
from app.reviews.pr_agent_client import AI_FINDING_CWE, review_diff_with_pr_agent
from app.reviews.rag_client import query_rag_guidance
from app.reviews.report_formatter import format_pr_comment
from app.reviews.risk import calculate_risk_score, decide_verdict, get_suggested_fix
from app.security.github_app import fetch_pull_request_diff, post_pr_comment

logger = logging.getLogger("main_server")


async def process_single_job(job_data: dict) -> None:
    job_id = job_data["job_id"]
    org_id = job_data["organization_id"]
    repo_id = job_data["repository_id"]
    pr_number = job_data.get("pr_number", 0)
    commit_sha = job_data.get("commit_sha", "HEAD")
    code_content = job_data.get("code_content", "")
    file_path = job_data.get("file_path", "unknown")
    is_diff = job_data.get("is_diff", False)
    repo_full_name = job_data.get("repo_full_name")
    installation_id = job_data.get("installation_id")

    factory = get_session_factory()
    async with factory() as db:
        # 1. Update job to processing
        stmt = select(ReviewJob).where(ReviewJob.id == job_id)
        job = (await db.execute(stmt)).scalar_one_or_none()
        if job:
            job.status = "processing"
            await db.commit()

        # 1b. The webhook handler enqueues immediately without fetching the
        # diff (GitHub expects an ACK within ~10s; a full review can take
        # much longer). The diff fetch - the slow, network-bound part -
        # happens here instead, off GitHub's request path entirely.
        if is_diff and not code_content and repo_full_name and installation_id:
            try:
                code_content = await fetch_pull_request_diff(repo_full_name, pr_number, installation_id)
            except Exception as e:
                logger.error(f"Failed to fetch PR diff for job {job_id}: {e}")
                if job:
                    job.status = "failed"
                    job.error_message = f"diff fetch failed: {e}"
                    await db.commit()
                return

        # 2. Run deterministic static scans with exact diff line coordinate mapping
        if is_diff:
            findings_raw = []
            for path, patch in split_diff_by_file(code_content).items():
                added_lines = extract_added_lines(patch)
                findings_raw.extend(scan_diff_lines(added_lines, file_path=path))
        else:
            findings_raw = scan_source_code(code_content, file_path=file_path)

        # 2b. Run the pr_agent LLM review stage (additive, best-effort - see
        # docs/PR_AGENT_INTEGRATION_GUIDE.md). Only meaningful on real diffs,
        # and only when an LLM key is configured.
        settings = get_settings()
        if is_diff and settings.pr_agent_review_enabled:
            ai_findings = await review_diff_with_pr_agent(code_content, default_file_path=file_path)
            existing_keys = {(f["file_path"], f["line_number"], f["title"]) for f in findings_raw}
            for f in ai_findings:
                key = (f["file_path"], f["line_number"], f["title"])
                if key not in existing_keys:
                    findings_raw.append(f)
                    existing_keys.add(key)

        risk_score = calculate_risk_score(findings_raw)
        verdict = decide_verdict(risk_score)

        # 3. Enrich with RAG guidance
        findings_to_insert = []
        any_rag_success = False

        for f in findings_raw:
            cwe = f["cwe_id"]
            is_ai_finding = cwe == AI_FINDING_CWE
            # An AI finding has no real CWE to filter the RAG lookup by; let
            # title-based matching alone decide relevance instead of a cwe_id
            # that can never match a stored OWASP chunk.
            guidance, _, ok = await query_rag_guidance(query=f["title"], cwe_id=None if is_ai_finding else cwe)
            if ok:
                any_rag_success = True

            if is_ai_finding:
                # pr_agent's own explanation carries more signal than the
                # generic CWE-keyed template in risk.py - use it directly.
                fix = f.get("explanation") or "Review this AI-flagged issue manually."
                if guidance:
                    fix = f"{fix}\nOWASP Guidance: {guidance}"
            else:
                fix = get_suggested_fix(cwe, guidance)

            findings_to_insert.append({
                "cwe_id": cwe,
                "severity": f["severity"],
                "title": f["title"],
                "file_path": f["file_path"],
                "line_number": f["line_number"],
                "code_snippet": f["code_snippet"],
                "suggested_fix": fix,
            })

        # 4. Create review record
        summary = (
            f"Found {len(findings_raw)} issue(s). "
            f"Risk score: {risk_score}/100. Verdict: {verdict}."
        ) if findings_raw else "No security issues detected."

        review = Review(
            organization_id=org_id,
            repository_id=repo_id,
            job_id=job_id,
            pr_number=pr_number,
            commit_sha=commit_sha,
            risk_score=risk_score,
            verdict=verdict,
            summary=summary,
            guidance_available=any_rag_success or len(findings_raw) == 0,
        )
        db.add(review)
        await db.flush()

        for fin in findings_to_insert:
            db.add(Finding(review_id=review.id, organization_id=org_id, **fin))

        if job:
            job.status = "completed"

        # 5. Record audit event
        db.add(AuditEvent(
            organization_id=org_id,
            action="review_completed",
            resource_type="review",
            resource_id=review.id,
            details_json=f'{{"pr_number": {pr_number}, "verdict": "{verdict}"}}',
        ))

        await db.commit()
        logger.info(f"Processed review job {job_id} -> Verdict: {verdict}")

        # 6. Post the formatted result as a PR comment. GitHub's own email
        # notifications fire for this automatically for anyone watching the
        # PR - no mail-sending code needed on our side.
        if repo_full_name and installation_id:
            try:
                comment_body = format_pr_comment(verdict, risk_score, findings_to_insert, commit_sha)
                await post_pr_comment(repo_full_name, pr_number, installation_id, comment_body)
            except Exception as e:
                logger.warning(f"Failed to post PR comment for job {job_id}: {e}")


async def run_worker_loop() -> None:
    settings = get_settings()
    setup_logger(settings.redis_url)
    logger.info("Starting main-server review worker loop...")

    while True:
        try:
            job = await dequeue_review_job(timeout=2)
            if job:
                await process_single_job(job)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker encountered error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run_worker_loop())
