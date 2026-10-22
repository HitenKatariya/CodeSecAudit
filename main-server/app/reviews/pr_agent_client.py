"""LLM-based review stage backed by the vendored pr_agent library.

See docs/PR_AGENT_INTEGRATION_GUIDE.md (Pattern B) for the upstream shape this
follows: PlainDiffGitProvider feeds a raw unified diff into PRReviewer, and the
structured review comes back as a dict instead of a published PR comment.
"""

import logging
from typing import Any
from app.core.config import get_settings as get_app_settings

logger = logging.getLogger("main_server")

# AI findings don't map to a specific CWE; this keeps Finding.cwe_id non-null
# without pretending to a classification the model didn't give us.
AI_FINDING_CWE = "AI-REVIEW"

_RISK_TO_SEVERITY = {"high": "critical", "medium": "high", "low": "medium"}

_SECURITY_EXTRA_INSTRUCTIONS = (
    "You are performing a SECURITY-focused review, not a general code review. "
    "Prioritize: injection (SQL/command/code), SSRF, auth/authz bypass, insecure "
    "deserialization, path traversal, hardcoded secrets, weak crypto, and unvalidated "
    "user input reaching a sensitive sink. Name the likely CWE in each issue_header "
    "when identifiable (e.g. 'SQL Injection (CWE-89)'). Ignore pure style/readability nits."
)


async def review_diff_with_pr_agent(diff_text: str, default_file_path: str = "unknown") -> list[dict[str, Any]]:
    """Run pr_agent's PRReviewer over a raw diff and return Finding-shaped dicts.

    Returns an empty list on any failure (missing model key, parse error, no
    issues found) - this stage is additive on top of the deterministic engine,
    never load-bearing for it.
    """
    if not diff_text.strip():
        return []

    try:
        from pr_agent.config_loader import get_settings as get_pr_agent_settings
        from pr_agent.tools.pr_reviewer import PRReviewer
    except ImportError:
        logger.warning("pr_agent is not installed; skipping AI review stage")
        return []

    app_settings = get_app_settings()
    pr_settings = get_pr_agent_settings()
    pr_settings.set("CONFIG.MODEL", app_settings.pr_agent_model)
    fallback_models = [m.strip() for m in app_settings.pr_agent_fallback_models.split(",") if m.strip()]
    pr_settings.set("CONFIG.FALLBACK_MODELS", fallback_models)
    # litellm's own cost map doesn't know nvidia_nim/* or huggingface/* model
    # ids, so its token-budget step refuses to run at all unless told the
    # context window explicitly (confirmed against
    # pr_agent/algo/token_budget.py - this is not optional for either
    # fallback). Llama-3.1-class models support 128k; this is a safe
    # conservative floor, not the model's true max.
    pr_settings.set("CONFIG.CUSTOM_MODEL_MAX_TOKENS", 32000)
    # Setting plain_diff.content routes get_git_provider_with_context() to the
    # plain-diff provider regardless of config.git_provider (see
    # pr_agent/git_providers/__init__.py:get_git_provider_with_context).
    pr_settings.set("PLAIN_DIFF.CONTENT", diff_text)
    pr_settings.set("PLAIN_DIFF.OUTPUT_PATH", None)
    pr_settings.set("PLAIN_DIFF.JSON_OUTPUT_PATH", None)
    # require_risk_assessment defaults to false in pr_agent/settings/configuration.toml,
    # which means review.risk_level (read below) would always come back None -
    # every AI finding silently degrading to "medium" severity. Force it on.
    pr_settings.set("PR_REVIEWER.REQUIRE_RISK_ASSESSMENT", True)
    pr_settings.set("PR_REVIEWER.EXTRA_INSTRUCTIONS", _SECURITY_EXTRA_INSTRUCTIONS)
    pr_settings.set("PR_REVIEWER.NUM_MAX_FINDINGS", 10)

    try:
        reviewer = PRReviewer(pr_url=None)
        await reviewer.run()
    except Exception as e:
        logger.warning(f"pr_agent review failed, continuing without AI findings: {e}")
        return []

    structured = getattr(reviewer, "_structured_review_data", None)
    if not structured:
        return []

    review = structured.get("review", {})
    severity = _RISK_TO_SEVERITY.get(review.get("risk_level"), "medium")
    findings: list[dict[str, Any]] = []

    security_concerns = review.get("security_concerns") or ""

    for issue in review.get("key_issues_to_review", []):
        explanation = issue.get("issue_content", "")
        if security_concerns:
            explanation = f"{explanation}\n\nOverall PR security concerns: {security_concerns}".strip()
        findings.append({
            "file_path": issue.get("relevant_file") or default_file_path,
            "line_number": issue.get("start_line") or 0,
            "cwe_id": AI_FINDING_CWE,
            "severity": severity,
            "title": issue.get("issue_header", "AI-flagged issue"),
            "explanation": explanation,
            "code_snippet": "",
        })

    return findings
