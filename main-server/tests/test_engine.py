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
    assert score == 0
    assert decide_verdict(score) == "APPROVE"
