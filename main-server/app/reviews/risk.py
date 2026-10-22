"""Risk scoring, verdict determination, and fix recommendations."""

from typing import Any

SEVERITY_POINTS = {
    "critical": 35,
    "high": 25,
    "medium": 15,
    "low": 5,
}

FIX_TEMPLATES = {
    "CWE-94": "Replace eval() / exec() with safe parsers (e.g., JSON.parse() or ast.literal_eval).",
    "CWE-89": "Use parameterized queries or prepared statements instead of string concatenation.",
    "CWE-78": "Avoid shell=True; pass arguments as an explicit sequence to subprocess.run().",
    "CWE-328": "Replace MD5/SHA-1 with SHA-256 for integrity or bcrypt/argon2 for password hashing.",
    "CWE-798": "Store credentials in environment variables or a secrets manager, never hardcoded in source.",
    "CWE-22": "Validate paths using os.path.realpath() and verify prefix matches the allowed directory.",
    "CWE-918": "Validate target URLs against a strict allowlist and block internal IP addresses (RFC 1918).",
}


def calculate_risk_score(findings: list[dict[str, Any]]) -> int:
    total = sum(SEVERITY_POINTS.get(f.get("severity", "medium"), 10) for f in findings)
    return min(total, 100)


def decide_verdict(risk_score: int) -> str:
    if risk_score >= 60:
        return "REQUEST_CHANGES"
    if risk_score >= 20:
        return "WARNING"
    return "APPROVE"


def get_suggested_fix(cwe_id: str, guidance: str = "") -> str:
    if cwe_id in FIX_TEMPLATES:
        base = FIX_TEMPLATES[cwe_id]
        return f"{base}\nOWASP Guidance: {guidance}" if guidance else base
    return "Sanitize and validate all user inputs before passing to sensitive operations."
