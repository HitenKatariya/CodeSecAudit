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


def test_citations_and_agent_payload():
    import json
    import re

    findings = [
        {
            "cwe_id": "CWE-89",
            "severity": "critical",
            "title": "SQL Injection via String Concatenation",
            "file_path": "app/db.py",
            "line_number": 42,
            "code_snippet": 'db.execute("SELECT * FROM users WHERE id = " + user_id)',
            "suggested_fix": "Use parameterized queries.",
        },
        {
            "cwe_id": "CWE-78",
            "severity": "critical",
            "title": "OS Command Injection via subprocess/shell",
            "file_path": "app/cmd.py",
            "line_number": 15,
            "code_snippet": 'subprocess.run(f"echo {user_input}", shell=True)',
            "suggested_fix": "Avoid shell=True.",
        },
    ]
    body = format_pr_comment("REQUEST_CHANGES", 9.80, findings, "commit123456789")

    # Verify exact CWE MITRE links
    assert "[CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)" in body
    assert "[CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)" in body

    # Verify OWASP ASVS Benchmark citations
    assert "OWASP ASVS v4.0.3 §5.3.4 (Parameterized Queries Required)" in body
    assert "OWASP ASVS v4.0.3 §5.3.8 (OS Command Injection Protection)" in body

    # Verify CODESEC_AGENT_PAYLOAD block
    match = re.search(r"<!-- CODESEC_AGENT_PAYLOAD_START\s*(\{.*?\})\s*CODESEC_AGENT_PAYLOAD_END -->", body, re.DOTALL)
    assert match is not None, "CODESEC_AGENT_PAYLOAD block not found in comment"

    payload_data = json.loads(match.group(1))
    assert payload_data["schema_version"] == "1.0.0"
    assert payload_data["verdict"] == "REQUEST_CHANGES"
    assert payload_data["cvss_score"] == 9.80
    assert len(payload_data["findings"]) == 2
    assert payload_data["findings"][0]["cwe_id"] in ("CWE-89", "CWE-78")
    assert payload_data["findings"][0]["owasp_asvs"].startswith("OWASP ASVS v4.0.3")


def test_agent_payload_no_findings():
    import json
    import re

    body = format_pr_comment("APPROVE", 0.0, [], "commit123456789")
    match = re.search(r"<!-- CODESEC_AGENT_PAYLOAD_START\s*(\{.*?\})\s*CODESEC_AGENT_PAYLOAD_END -->", body, re.DOTALL)
    assert match is not None
    payload_data = json.loads(match.group(1))
    assert payload_data["schema_version"] == "1.0.0"
    assert payload_data["verdict"] == "APPROVE"
    assert payload_data["cvss_score"] == 0.0
    assert payload_data["findings"] == []

