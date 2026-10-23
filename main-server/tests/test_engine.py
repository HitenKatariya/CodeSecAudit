"""Test review detector engine."""

from app.reviews.engine import scan_source_code
from app.reviews.risk import calculate_risk_score, decide_verdict


def test_detect_eval():
    findings = scan_source_code("result = eval(user_input)", file_path="app.py")
    assert len(findings) == 1
    assert findings[0]["cwe_id"] == "CWE-94"
    assert findings[0]["severity"] == "critical"


def test_detect_sql_injection():
    findings = scan_source_code('cursor.execute("SELECT * FROM users WHERE id = " + user_id)', file_path="db.py")
    assert len(findings) == 1
    assert findings[0]["cwe_id"] == "CWE-89"


def test_suppression():
    code = "result = eval(user_input)  # codesec-ignore: CWE-94"
    findings = scan_source_code(code, file_path="app.py")
    assert len(findings) == 0


def test_clean_code():
    code = """
    def add(a: int, b: int) -> int:
        return a + b
    """
    findings = scan_source_code(code, file_path="math.py")
    assert len(findings) == 0
    score = calculate_risk_score(findings)
    assert score == 0.0
    assert decide_verdict(score) == "APPROVE"


def test_scan_diff_lines_preserves_coordinates():
    from app.reviews.engine import scan_diff_lines

    lines_with_numbers = [
        (45, 'result = eval(user_input)'),
        (52, 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'),
    ]
    findings = scan_diff_lines(lines_with_numbers, file_path="main.py")
    assert len(findings) == 2
    assert findings[0]["line_number"] == 45
    assert findings[0]["cwe_id"] == "CWE-94"
    assert findings[1]["line_number"] == 52
    assert findings[1]["cwe_id"] == "CWE-89"


def test_cvss_risk_score_calculation():
    findings = [
        {"cwe_id": "CWE-78", "severity": "critical"},
        {"cwe_id": "CWE-89", "severity": "critical"},
        {"cwe_id": "CWE-328", "severity": "medium"},
    ]
    score = calculate_risk_score(findings)
    assert 9.0 <= score <= 10.0
    # CVSS scores are rounded to 2 decimal places
    assert score == round(score, 2)
    assert decide_verdict(score) == "REQUEST_CHANGES"

    low_findings = [{"cwe_id": "CWE-999", "severity": "low"}]
    low_score = calculate_risk_score(low_findings)
    assert low_score == 2.54
    assert decide_verdict(low_score) == "APPROVE"
