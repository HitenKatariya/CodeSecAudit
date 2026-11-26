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
