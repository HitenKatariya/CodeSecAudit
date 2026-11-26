"""Formats a completed review as an in-depth, enterprise-grade GitHub-flavored Markdown PR comment."""

import json
from typing import Any
from app.reviews.risk import get_cwe_details
from app.core.config import get_settings
from app.reviews.diff_analyzer import DiffAnalysis, analyze_diff
from app.reviews.flow_analyzer import FlowComparison, generate_flow_comparison

_VERDICT_BADGE = {
    "APPROVE": "✅ **APPROVE**",
    "WARNING": "⚠️ **WARNING**",
    "REQUEST_CHANGES": "🛑 **REQUEST CHANGES**",
}

_SEVERITY_BADGE = {
    "critical": "🔴 `CRITICAL`",
    "high": "🟠 `HIGH`",
    "medium": "🟡 `MEDIUM`",
    "low": "🔵 `LOW`",
}

_SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}

OWASP_ASVS_BENCHMARKS: dict[str, str] = {
    "CWE-89": "OWASP ASVS v4.0.3 §5.3.4 (Parameterized Queries Required)",
    "CWE-78": "OWASP ASVS v4.0.3 §5.3.8 (OS Command Injection Protection)",
    "CWE-94": "OWASP ASVS v4.0.3 §5.2.4 (Dynamic Code Execution Avoidance)",
    "CWE-328": "OWASP ASVS v4.0.3 §6.2.2 (Cryptographic Hash Algorithms)",
    "CWE-798": "OWASP ASVS v4.0.3 §3.6.1 (Secrets and Credentials Storage)",
    "CWE-22": "OWASP ASVS v4.0.3 §12.3.1 (Path Traversal Protection)",
    "CWE-918": "OWASP ASVS v4.0.3 §12.6.1 (SSRF Protection & URL Validation)",
    "CWE-502": "OWASP ASVS v4.0.3 §5.5.1 (Deserialization Security)",
    "CWE-79": "OWASP ASVS v4.0.3 §5.1.3 (Output Encoding & Contextual Escaping)",
    "CWE-352": "OWASP ASVS v4.0.3 §4.2.1 (Anti-CSRF Mechanisms)",
}

CWE_TITLES: dict[str, str] = {
    "CWE-89": "SQL Injection",
    "CWE-78": "OS Command Injection",
    "CWE-94": "Code Injection",
    "CWE-328": "Use of Weak Hash",
    "CWE-798": "Use of Hard-coded Credentials",
    "CWE-22": "Path Traversal",
    "CWE-918": "Server-Side Request Forgery",
    "CWE-502": "Deserialization of Untrusted Data",
    "CWE-79": "Cross-Site Scripting",
    "CWE-352": "Cross-Site Request Forgery",
}


def get_cwe_mitre_link(cwe_id: str) -> str:
    """Generate exact CWE MITRE link, e.g. [CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)."""
    if not cwe_id or cwe_id == "AI-REVIEW":
        return "🤖 `AI-REVIEW`"
    cwe_num = cwe_id.replace("CWE-", "")
    title = CWE_TITLES.get(cwe_id, "Security Weakness")
    return f"[{cwe_id}: {title}](https://cwe.mitre.org/data/definitions/{cwe_num}.html)"


def get_asvs_citation(cwe_id: str) -> str:
    """Return OWASP ASVS Benchmark citation, e.g. OWASP ASVS v4.0.3 §5.3.4 (Parameterized Queries Required)."""
    return OWASP_ASVS_BENCHMARKS.get(cwe_id, "OWASP ASVS v4.0.3 (Standard Security Controls)")


def _build_agent_payload(verdict: str, risk_score: float, findings: list[dict[str, Any]]) -> str:
    payload = {
        "schema_version": "1.0.0",
        "verdict": verdict,
        "cvss_score": round(float(risk_score), 2),
        "findings": [
            {
                "cwe_id": f.get("cwe_id", "AI-REVIEW"),
                "severity": f.get("severity", "medium"),
                "title": f.get("title", ""),
                "file_path": f.get("file_path", "unknown"),
                "line_number": f.get("line_number", 0),
                "code_snippet": f.get("code_snippet", ""),
                "patch_suggested": f.get("suggested_fix") or f.get("explanation") or "",
                "cwe_mitre_url": f"https://cwe.mitre.org/data/definitions/{f.get('cwe_id', '').replace('CWE-', '')}.html" if str(f.get("cwe_id", "")).startswith("CWE-") else "",
                "owasp_asvs": get_asvs_citation(f.get("cwe_id", "")),
            }
            for f in findings
        ],
    }
    return f"<!-- CODESEC_AGENT_PAYLOAD_START\n{json.dumps(payload, indent=2)}\nCODESEC_AGENT_PAYLOAD_END -->"


def _render_modified_files_table(diff_analysis: DiffAnalysis) -> list[str]:
    lines = [
        "---",
        "### 📁 Modified Files Breakdown",
        "",
        f"**Total Files Changed:** `{diff_analysis.total_files}` &nbsp;|&nbsp; **Additions:** `+{diff_analysis.total_additions}` &nbsp;|&nbsp; **Deletions:** `-{diff_analysis.total_deletions}`",
        "",
        "| File Path | Status | Additions | Deletions | Net Lines |",
        "|:---|:---:|:---:|:---:|:---:|",
    ]
    for f in diff_analysis.files:
        status_badge = "🟢 Added" if f.status == "added" else ("🔴 Deleted" if f.status == "deleted" else "🟡 Modified")
        net = f.additions - f.deletions
        net_str = f"+{net}" if net >= 0 else str(net)
        lines.append(f"| `{f.path}` | {status_badge} | `+{f.additions}` | `-{f.deletions}` | `{net_str}` |")
    lines.append("")
    return lines


def _render_change_breakdown(diff_analysis: DiffAnalysis) -> list[str]:
    lines = [
        "### 🔄 Semantic Delta: What Changed / Added / Removed",
        "",
    ]
    if diff_analysis.overall_added:
        lines.append("**✨ What Added:**")
        for item in diff_analysis.overall_added[:15]:
            lines.append(f"- {item}")
        lines.append("")
    if diff_analysis.overall_changed:
        lines.append("**⚡ What Changed:**")
        for item in diff_analysis.overall_changed[:15]:
            lines.append(f"- {item}")
        lines.append("")
    if diff_analysis.overall_removed:
        lines.append("**🗑️ What Removed:**")
        for item in diff_analysis.overall_removed[:15]:
            lines.append(f"- {item}")
        lines.append("")
    return lines


def _render_flow_comparison(flow_comparison: FlowComparison) -> list[str]:
    lines = [
        "### 🔀 Architecture & Execution Flow: Before vs. After",
        "",
        "| Aspect | Flow Before PR | Flow After PR |",
        "|:---|:---|:---|",
        f"| **Execution Architecture** | {flow_comparison.flow_before_description} | {flow_comparison.flow_after_description} |",
        "",
        "**Flow Diagram Comparison:**",
        "",
        flow_comparison.mermaid_diagram,
        "",
        "**Key Architectural Observations:**",
    ]
    for note in flow_comparison.security_architecture_notes:
        lines.append(f"- {note}")
    lines.append("")
    return lines


def format_pr_comment(
    verdict: str,
    risk_score: float,
    findings: list[dict[str, Any]],
    commit_sha: str,
    diff_text: str = "",
    diff_analysis: DiffAnalysis | None = None,
    flow_comparison: FlowComparison | None = None,
) -> str:
    badge = _VERDICT_BADGE.get(verdict, verdict)
    short_sha = commit_sha[:12] if commit_sha else "HEAD"
    try:
        raw_url = get_settings().next_public_app_url.rstrip("/")
        dashboard_url = raw_url if raw_url and "localhost" not in raw_url else "https://codesec-client-v6a6.onrender.com"
    except Exception:
        dashboard_url = "https://codesec-client-v6a6.onrender.com"

    # Risk assessment description according to CVSS v3.1 thresholds
    if risk_score >= 7.0:
        risk_level_desc = "🚨 **Critical / High Security Risk** — Severe or exploitable vulnerabilities present. Immediate remediation required."
        merge_gate = "🚫 **MERGE BLOCKED:** High-risk vulnerabilities must be remediated or explicitly suppressed before merging."
    elif risk_score >= 4.0:
        risk_level_desc = "⚠️ **Elevated Medium Risk** — Security weaknesses identified that may introduce vulnerabilities into production."
        merge_gate = "⚠️ **MERGE CAUTION:** Security review recommended before deployment."
    else:
        risk_level_desc = "🛡️ **Low / Acceptable Risk** — No critical or high severity security vulnerabilities detected."
        merge_gate = "✅ **MERGE ALLOWED:** Standard peer review can proceed."

    lines = [
        "## 🛡️ CodeSecAudit AI — Comprehensive Security Audit Report",
        "",
        f"> **Verdict:** {badge} &nbsp;|&nbsp; **CVSS Security Risk Score:** `{risk_score:.2f} / 10.0` &nbsp;|&nbsp; **Target Commit:** `{short_sha}`",
        ">",
        f"> {risk_level_desc}",
        ">",
        f"> {merge_gate}",
        "",
    ]

    if diff_analysis is None and diff_text:
        diff_analysis = analyze_diff(diff_text)
    if flow_comparison is None and diff_analysis:
        flow_comparison = generate_flow_comparison(diff_analysis, findings)

    if diff_analysis:
        lines.extend(_render_modified_files_table(diff_analysis))
        lines.extend(_render_change_breakdown(diff_analysis))
    if flow_comparison:
        lines.extend(_render_flow_comparison(flow_comparison))

    if not findings:
        agent_payload = _build_agent_payload(verdict, risk_score, [])
        lines.extend([
            "---",
            "### 🔍 Audit Findings",
            "",
            "✨ **No security issues detected in this diff.**",
            "",
            "All scanned lines pass OWASP Top 10 automated security policies and pattern baselines.",
            "",
            agent_payload,
            "",
            "---",
            f"<sub>Report generated by **CodeSecAudit AI** • Automated Pull Request Security Agent • [Documentation & Dashboard]({dashboard_url})</sub>",
        ])
        return "\n".join(lines)


    # Sort findings critical -> high -> medium -> low
    sorted_findings = sorted(findings, key=lambda x: _SEVERITY_RANK.get(x.get("severity", "low"), 0), reverse=True)

    # Count breakdown
    crit_count = sum(1 for f in sorted_findings if f.get("severity") == "critical")
    high_count = sum(1 for f in sorted_findings if f.get("severity") == "high")
    med_count = sum(1 for f in sorted_findings if f.get("severity") == "medium")
    low_count = sum(1 for f in sorted_findings if f.get("severity") == "low")

    unique_files = len({f.get("file_path", "unknown") for f in sorted_findings})

    lines.extend([
        "---",
        "### 📊 Executive Summary & Triage Matrix",
        "",
        f"Automated multi-layer security evaluation discovered **{len(sorted_findings)} finding(s)** across **{unique_files} file(s)**:",
        f"- 🔴 **{crit_count} Critical Severity** — High probability of direct exploitation or severe impact.",
        f"- 🟠 **{high_count} High Severity** — Significant security weakness or cryptographic flaw.",
        f"- 🟡 **{med_count} Medium Severity** — Security configuration or validation gap.",
        f"- 🔵 **{low_count} Low Severity** — Best practice or defensive hardening observation.",
        "",
        "| Severity | CWE ID | Category | Location | Vulnerability Title | Action |",
        "|:---:|:---:|:---:|:---|:---|:---:|",
    ])

    for f in sorted_findings:
        sev = f.get("severity", "medium")
        sev_badge = _SEVERITY_BADGE.get(sev, f"`{sev.upper()}`")
        cwe_id = f.get("cwe_id", "AI-REVIEW")
        title = f.get("title", "")
        file_path = f.get("file_path", "unknown")
        line_no = f.get("line_number", "?")

        cwe_info = get_cwe_details(cwe_id)
        if cwe_info:
            cwe_link = f"[`{cwe_id}`]({cwe_info['cwe_url']})"
            category = cwe_info.get("owasp", "OWASP Top 10")
        elif cwe_id == "AI-REVIEW":
            cwe_link = "🤖 `AI-REVIEW`"
            category = "LLM Threat Model"
        else:
            cwe_link = f"`{cwe_id}`"
            category = "Security Defect"

        loc_link = f"`{file_path}:{line_no}`"
        action = "🔴 Fix Required" if sev in ("critical", "high") else "🟡 Review"

        lines.append(f"| {sev_badge} | {cwe_link} | {category} | {loc_link} | **{title}** | {action} |")

    lines.extend([
        "",
        "---",
        "### 🔬 Detailed Vulnerability Deep-Dives & Remediation Guides",
        "",
    ])

    for idx, f in enumerate(sorted_findings, start=1):
        sev = f.get("severity", "medium")
        sev_badge = _SEVERITY_BADGE.get(sev, f"`{sev.upper()}`")
        cwe_id = f.get("cwe_id", "AI-REVIEW")
        title = f.get("title", "Security Finding")
        file_path = f.get("file_path", "unknown")
        line_no = f.get("line_number", "?")
        snippet = f.get("code_snippet", "").strip()
        explanation = f.get("explanation", "").strip()
        suggested_fix = f.get("suggested_fix", "").strip()

        cwe_info = get_cwe_details(cwe_id)

        lines.append(f"#### {idx}. {sev_badge} {title}")
        lines.append(f"- **File:** `{file_path}` (Line `{line_no}`)")
        cwe_mitre_link = get_cwe_mitre_link(cwe_id)
        asvs_cite = get_asvs_citation(cwe_id)
        lines.append(f"- **CWE MITRE Reference:** {cwe_mitre_link}")
        lines.append(f"- **OWASP ASVS Benchmark:** `{asvs_cite}`")
        if cwe_info:
            lines.append(f"- **Classification:** [{cwe_id} — {cwe_info['full_name']}]({cwe_info['cwe_url']})")
            lines.append(f"- **OWASP Category:** `{cwe_info.get('owasp', 'A03:2021')}`")
        lines.append("")

        # Code snippet if available
        if snippet:
            lines.extend([
                "**Flagged Code Snippet:**",
                "```python",
                f"# Line {line_no} in {file_path}",
                snippet,
                "```",
                "",
            ])

        # Technical description & attack vector
        if cwe_info:
            lines.extend([
                "**Technical Vulnerability Analysis:**",
                f"{cwe_info['description']}",
                "",
                "**Exploit Scenario & Attack Vector:**",
                f"{cwe_info['attack_vector']}",
                "",
                "**Security Impact:**",
                f"{cwe_info['impact']}",
                "",
                "**Remediation Action Plan:**",
            ])
            for pt in cwe_info.get("remediation_points", []):
                lines.append(f"1. {pt}")
            lines.append("")

            if cwe_info.get("secure_example"):
                lines.extend([
                    "**Production-Ready Secure Implementation:**",
                    "```python",
                    cwe_info["secure_example"],
                    "```",
                    "",
                ])
        elif explanation:
            lines.extend([
                "**AI Threat Model & Vulnerability Details:**",
                explanation,
                "",
            ])

        # Suggested fix or RAG guidance if present
        if suggested_fix and "OWASP Guidance:" in suggested_fix:
            rag_parts = suggested_fix.split("OWASP Guidance:", 1)
            rag_guidance = rag_parts[1].strip()
            if rag_guidance:
                lines.extend([
                    "> 📖 **RAG / OWASP Knowledge Base Guidance:**",
                    f"> {rag_guidance}",
                    "",
                ])
        elif suggested_fix and not cwe_info:
            lines.extend([
                "**Recommended Action:**",
                f"> {suggested_fix}",
                "",
            ])

        # False positive suppression instruction
        suppress_token = cwe_id if cwe_id != "AI-REVIEW" else "AI-REVIEW"
        lines.extend([
            f"*To suppress this finding if deliberate (e.g. test fixture), append `# codesec-ignore: {suppress_token}` to line {line_no}.*",
            "",
            "---",
            "",
        ])

    agent_payload = _build_agent_payload(verdict, risk_score, sorted_findings)

    lines.extend([
        "### 📋 Defense-in-Depth & Pre-Merge Checklist",
        "",
        "Before merging this pull request into production, verify each of the following security requirements:",
        "- [ ] **Input Sanitization & Parameterization:** Replace all string concatenation in database and system commands with parameterized interfaces.",
        "- [ ] **Process Isolation:** Avoid `shell=True` and invoke binaries directly with strictly validated arguments.",
        "- [ ] **Safe Parsers:** Never execute untrusted expressions with `eval()` or `exec()`; use `json.loads()` or `ast.literal_eval()`.",
        "- [ ] **Cryptographic Modernization:** Migrate legacy algorithms (MD5/SHA1) to SHA-256 for digests and Argon2id / bcrypt for credentials.",
        "- [ ] **Regression Testing:** Verify that test suites and security integration checks pass.",
        "",
        agent_payload,
        "",
        "---",
        f"<sub>Report generated by **CodeSecAudit AI** • Automated Pull Request Security Agent • [Documentation & Dashboard]({dashboard_url})</sub>",
    ])

    return "\n".join(lines)
