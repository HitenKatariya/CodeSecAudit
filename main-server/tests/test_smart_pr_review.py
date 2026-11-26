"""Tests for smart PR review diff analysis, change breakdown, and execution flow comparison."""

import pytest
from app.reviews.diff_analyzer import analyze_diff
from app.reviews.flow_analyzer import generate_flow_comparison
from app.reviews.report_formatter import format_pr_comment

SAMPLE_DIFF = """diff --git a/app/api/service.py b/app/api/service.py
new file mode 100644
--- /dev/null
+++ b/app/api/service.py
@@ -0,0 +1,15 @@
+import sqlite3
+from fastapi import APIRouter
+
+router = APIRouter()
+
+@router.get("/users")
+def get_users(user_id: str):
+    query = "SELECT * FROM users WHERE id = '" + user_id + "'"
+    return query
+
+def calculate_total(a: int, b: int):
+    return a + b
+"""


def test_analyze_diff_extracts_files_and_symbols():
    diff_analysis = analyze_diff(SAMPLE_DIFF)
    assert diff_analysis.total_files == 1
    assert diff_analysis.total_additions > 0
    assert diff_analysis.total_deletions == 0

    file_summary = diff_analysis.files[0]
    assert file_summary.path == "app/api/service.py"
    assert file_summary.status == "added"
    assert any("get_users" in sym for sym in file_summary.added_symbols)
    assert any("calculate_total" in sym for sym in file_summary.added_symbols)
    assert len(diff_analysis.overall_added) > 0


def test_flow_comparison_generation():
    diff_analysis = analyze_diff(SAMPLE_DIFF)
    findings = [
        {
            "cwe_id": "CWE-89",
            "severity": "critical",
            "title": "SQL Injection",
            "file_path": "app/api/service.py",
            "line_number": 8,
        }
    ]
    flow = generate_flow_comparison(diff_analysis, findings)
    assert "Flow Before PR" in flow.mermaid_diagram
    assert "Flow After PR" in flow.mermaid_diagram
    assert "CWE-89" in flow.mermaid_diagram
    assert "Taint propagation" in flow.security_architecture_notes[0]


def test_format_pr_comment_renders_smart_review_sections():
    findings = [
        {
            "cwe_id": "CWE-89",
            "severity": "critical",
            "title": "SQL Injection",
            "file_path": "app/api/service.py",
            "line_number": 8,
            "code_snippet": 'query = "SELECT * FROM users WHERE id = \'" + user_id + "\'"',
            "suggested_fix": "Use parameterized queries.",
        }
    ]
    comment = format_pr_comment(
        verdict="REQUEST_CHANGES",
        risk_score=9.5,
        findings=findings,
        commit_sha="abcdef123456",
        diff_text=SAMPLE_DIFF,
    )

    # 1. Modified Files Breakdown section
    assert "### 📁 Modified Files Breakdown" in comment
    assert "`app/api/service.py`" in comment
    assert "🟢 Added" in comment

    # 2. Semantic Delta section
    assert "### 🔄 Semantic Delta: What Changed / Added / Removed" in comment
    assert "**✨ What Added:**" in comment

    # 3. Execution Flow Comparison section
    assert "### 🔀 Architecture & Execution Flow: Before vs. After" in comment
    assert "```mermaid" in comment
    assert "flowchart TD" in comment
    assert "Key Architectural Observations:" in comment

    # 4. Standard security audit and machine-readable payload
    assert "### 📊 Executive Summary & Triage Matrix" in comment
    assert "<!-- CODESEC_AGENT_PAYLOAD_START" in comment
