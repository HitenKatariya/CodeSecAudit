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

import re

_SECURITY_EXTRA_INSTRUCTIONS = (
    "ROLE: You are an elite Principal Application Security Architect and Lead Code Reviewer conducting a comprehensive, production-grade security audit.\n"
    "MISSION: Analyze the git diff meticulously for security vulnerabilities, logic bugs, architectural weaknesses, and data validation gaps. Be exhaustive, thorough, and highly technical. It is completely okay to take time to be detailed.\n"
    "\n"
    "AUDIT TARGETS (Strict Priority):\n"
    "1. INJECTION VULNERABILITIES: OS Command Injection (CWE-78), SQL Injection (CWE-89), Dynamic Code Execution (CWE-94), Template Injection (CWE-1336), XPath/LDAP Injection.\n"
    "2. BROKEN ACCESS CONTROL & SSRF: Server-Side Request Forgery (CWE-918), Path Traversal (CWE-22), IDOR / Broken Object-Level Authorization, privilege escalation.\n"
    "3. CRYPTOGRAPHIC & SECRETS FAILURES: Broken/deprecated hashing (MD5/SHA1/DES) (CWE-328), hardcoded tokens/passwords/API keys (CWE-798), static salt/IV, predictable PRNGs.\n"
    "4. INSECURE DESERIALIZATION & MEMORY: Unsafe YAML/pickle loading (CWE-502), prototype pollution, memory/buffer boundaries.\n"
    "5. AUTHENTICATION & SESSION: Insecure JWT validation (none algorithm, missing signature verify), missing CSRF/CORS defenses, rate-limiting gaps.\n"
    "\n"
    "OUTPUT FORMATTING REQUIREMENTS FOR EACH FINDING:\n"
    "- In 'issue_header': Format strictly as '[CWE-ID]: [Vulnerability Title]' (e.g. 'CWE-89: SQL Injection via String Concatenation').\n"
    "- In 'issue_content': Provide a rich, structured breakdown with:\n"
    "  • **Root Cause Analysis**: Why this code construct is vulnerable.\n"
    "  • **Attack Vector & Exploit Payload**: Realistic attack payload demonstrating how an adversary exploits this weakness.\n"
    "  • **Impact Assessment**: CVSS blast radius (Confidentiality, Integrity, Availability).\n"
    "  • **Remediation & Secure Code Fix**: Complete, production-ready replacement code snippet demonstrating the fix.\n"
    "  • **Defense-in-Depth Recommendation**: Architectural guardrail to prevent recurrence.\n"
    "\n"
    "QUALITY RULES: Ignore formatting, whitespace, variable naming, and pure style issues. Focus exclusively on security and defensive resilience."
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
    pr_settings.set("CONFIG.CUSTOM_MODEL_MAX_TOKENS", 32000)
    pr_settings.set("PLAIN_DIFF.CONTENT", diff_text)
    pr_settings.set("PLAIN_DIFF.OUTPUT_PATH", None)
    pr_settings.set("PLAIN_DIFF.JSON_OUTPUT_PATH", None)
    pr_settings.set("PR_REVIEWER.REQUIRE_RISK_ASSESSMENT", True)
    pr_settings.set("PR_REVIEWER.EXTRA_INSTRUCTIONS", _SECURITY_EXTRA_INSTRUCTIONS)
    pr_settings.set("PR_REVIEWER.NUM_MAX_FINDINGS", 15)

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
        header = issue.get("issue_header", "AI-flagged issue")
        explanation = issue.get("issue_content", "")
        if security_concerns:
            explanation = f"{explanation}\n\nOverall PR security concerns: {security_concerns}".strip()

        # Extract explicit CWE if the AI named it in the header
        cwe_match = re.search(r"CWE-(\d+)", header, re.IGNORECASE)
        cwe_id = f"CWE-{cwe_match.group(1)}" if cwe_match else AI_FINDING_CWE

        findings.append({
            "file_path": issue.get("relevant_file") or default_file_path,
            "line_number": issue.get("start_line") or 0,
            "cwe_id": cwe_id,
            "severity": severity,
            "title": header,
            "explanation": explanation,
            "code_snippet": "",
        })

    return findings
