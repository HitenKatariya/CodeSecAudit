"""Formats a completed review as a GitHub-flavored Markdown PR comment."""

from typing import Any

_VERDICT_BADGE = {
    "APPROVE": "✅ **APPROVE**",
    "WARNING": "⚠️ **WARNING**",
    "REQUEST_CHANGES": "🛑 **REQUEST CHANGES**",
}

_SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}

_SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}


def format_pr_comment(
    verdict: str,
    risk_score: int,
    findings: list[dict[str, Any]],
    commit_sha: str,
) -> str:
    badge = _VERDICT_BADGE.get(verdict, verdict)
    lines = [
        "## 🛡️ CodeSecAudit AI — Security Review",
        "",
        f"**Verdict:** {badge}  **Risk score:** {risk_score}/100  **Commit:** `{commit_sha[:12]}`",
        "",
    ]

    if not findings:
        lines.append("No security issues detected in this diff.")
        return "\n".join(lines)

    lines.append(f"Found **{len(findings)}** issue(s):")
    lines.append("")
    lines.append("| | Severity | CWE | Location | Issue |")
    lines.append("|---|---|---|---|---|")

    for f in sorted(findings, key=lambda x: _SEVERITY_RANK.get(x.get("severity"), 0), reverse=True):
        emoji = _SEVERITY_EMOJI.get(f.get("severity", "low"), "⚪")
        source = "🤖 AI" if f.get("cwe_id") == "AI-REVIEW" else f.get("cwe_id", "")
        location = f"`{f.get('file_path', 'unknown')}:{f.get('line_number', '?')}`"
        lines.append(f"| {emoji} | {f.get('severity', '')} | {source} | {location} | {f.get('title', '')} |")

    lines.append("")
    lines.append("<details><summary>Details & suggested fixes</summary>\n")
    for f in findings:
        lines.append(f"**{f.get('title', '')}** — `{f.get('file_path', 'unknown')}:{f.get('line_number', '?')}`")
        if f.get("suggested_fix"):
            lines.append(f"\n> {f['suggested_fix']}\n")
        lines.append("")
    lines.append("</details>")

    return "\n".join(lines)
