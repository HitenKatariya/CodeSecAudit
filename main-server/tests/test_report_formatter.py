"""Test PR comment formatting."""

from app.reviews.report_formatter import format_pr_comment


def test_no_findings():
    body = format_pr_comment("APPROVE", 0, [], "abc123")
    assert "No security issues" in body


def test_orders_critical_first():
    findings = [
        {"cwe_id": "AI-REVIEW", "severity": "medium", "title": "Missing validation", "file_path": "app.py", "line_number": 5},
        {"cwe_id": "CWE-89", "severity": "critical", "title": "SQL Injection", "file_path": "db.py", "line_number": 12},
    ]
    body = format_pr_comment("REQUEST_CHANGES", 9.40, findings, "abc123def4567890")
    assert body.index("SQL Injection") < body.index("Missing validation")
    assert "abc123def456" in body
    assert "9.40 / 10.0" in body
