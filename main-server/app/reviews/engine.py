"""Deterministic rule-based security detector engine."""

import re
from typing import Any, Optional

RULES: list[dict[str, Any]] = [
    {
        "id": "eval-call",
        "title": "Code Injection via eval()",
        "cwe_id": "CWE-94",
        "severity": "critical",
        "patterns": [r"\beval\s*\(", r"\bexec\s*\(", r"\bnew\s+Function\s*\("],
        "explanation": "Evaluating dynamic strings executes arbitrary code.",
    },
    {
        "id": "sql-concat",
        "title": "SQL Injection via String Concatenation",
        "cwe_id": "CWE-89",
        "severity": "critical",
        "patterns": [
            r"(?:SELECT|INSERT|UPDATE|DELETE)\s+.*?\+\s*(?:request|req\.|input|params)",
            r"execute\s*\(\s*['\"].*?['\"]\s*\+",
            r"query\s*\(\s*['\"].*?['\"]\s*\+",
            r"cursor\.execute\s*\(\s*['\"].*?['\"]\s*\+",
            r"(?:SELECT|INSERT|UPDATE|DELETE).*?f['\"].*?\{.*?\}",
        ],
        "explanation": "Building SQL queries with string concatenation allows SQL injection.",
    },
    {
        "id": "subprocess-shell",
        "title": "OS Command Injection via subprocess/shell",
        "cwe_id": "CWE-78",
        "severity": "critical",
        "patterns": [
            r"subprocess\.(?:call|Popen|run|check_output)\s*\(.*?shell\s*=\s*True",
            r"os\.system\s*\(",
            r"os\.popen\s*\(",
        ],
        "explanation": "Executing shell commands with user-influenced arguments can allow arbitrary command execution.",
    },
    {
        "id": "weak-hash",
        "title": "Weak Hashing Algorithm",
        "cwe_id": "CWE-328",
        "severity": "high",
        "patterns": [r"\bmd5\s*\(", r"\bsha1\s*\(", r"MessageDigest\.getInstance\s*\(\s*['\"](?:MD5|SHA-1)['\"]"],
        "explanation": "MD5 and SHA-1 are cryptographically broken.",
    },
    {
        "id": "hardcoded-secret",
        "title": "Hardcoded Credential / Secret",
        "cwe_id": "CWE-798",
        "severity": "critical",
        "patterns": [
            r"(?:api_key|apikey|api_secret|secret_key)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}",
            r"(?:password|passwd|pwd)\s*[:=]\s*['\"][A-Za-z0-9_!@#$%^&*()]{8,}",
        ],
        "explanation": "Hardcoded credentials in code are exposed to repository readers.",
    },
    {
        "id": "unsafe-path",
        "title": "Path Traversal via Unsafe File Access",
        "cwe_id": "CWE-22",
        "severity": "high",
        "patterns": [
            r"file\s*=\s*new\s+File\s*\(\s*(?:request|req\.|params|\.\.\.)",
            r"(?:open|read|write|delete)\s*\(\s*(?:request|req\.|params|\.\.\.)",
        ],
        "explanation": "Using unvalidated user input to construct file paths allows path traversal.",
    },
    {
        "id": "unsafe-url-fetch",
        "title": "Server-Side Request Forgery (SSRF)",
        "cwe_id": "CWE-918",
        "severity": "high",
        "patterns": [
            r"requests?\.(?:get|post|put|delete)\s*\(\s*(?:request|req\.|params|\.\.\.)",
            r"urllib\.(?:request|urlopen)\s*\(.*?(?:request|req\.|params|\.\.\.)",
        ],
        "explanation": "Making HTTP requests to URLs constructed from user input allows SSRF attacks.",
    },
]

MAX_FINDINGS_PER_RULE = 3
MAX_TOTAL_FINDINGS = 20


def _build_suppression_map(lines: list[str]) -> dict[int, Optional[set[str]]]:
    suppressed: dict[int, Optional[set[str]]] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if "codesec-ignore-next-line" in stripped:
            m = re.search(r"codesec-ignore-next-line\s*:\s*(CWE-\d+)", stripped)
            suppressed.setdefault(i + 2, set()).add(m.group(1)) if m else suppressed.update({i + 2: None})
        elif "codesec-ignore" in stripped:
            m = re.search(r"codesec-ignore\s*:\s*(CWE-\d+)", stripped)
            suppressed.setdefault(i + 1, set()).add(m.group(1)) if m else suppressed.update({i + 1: None})
    return suppressed


def scan_diff_lines(
    lines_with_numbers: list[tuple[int, str]],
    file_path: Optional[str] = None
) -> list[dict[str, Any]]:
    """Scan line tuples (line_number, line_content) preserving accurate git diff line coordinates."""
    findings = []
    rule_counts: dict[str, int] = {}
    seen = set()

    suppressed: dict[int, Optional[set[str]]] = {}
    for idx, (line_no, line) in enumerate(lines_with_numbers):
        stripped = line.strip()
        if not stripped:
            continue
        if "codesec-ignore-next-line" in stripped:
            m = re.search(r"codesec-ignore-next-line\s*:\s*(CWE-\d+)", stripped)
            next_line_no = lines_with_numbers[idx + 1][0] if idx + 1 < len(lines_with_numbers) else line_no + 1
            suppressed.setdefault(next_line_no, set()).add(m.group(1)) if m else suppressed.update({next_line_no: None})
        elif "codesec-ignore" in stripped:
            m = re.search(r"codesec-ignore\s*:\s*(CWE-\d+)", stripped)
            suppressed.setdefault(line_no, set()).add(m.group(1)) if m else suppressed.update({line_no: None})

    for line_no, line in lines_with_numbers:
        if len(findings) >= MAX_TOTAL_FINDINGS:
            break
        stripped = line.strip()
        if not stripped:
            continue

        for rule in RULES:
            if len(findings) >= MAX_TOTAL_FINDINGS or rule_counts.get(rule["id"], 0) >= MAX_FINDINGS_PER_RULE:
                continue

            for pattern in rule["patterns"]:
                if re.search(pattern, stripped, re.IGNORECASE):
                    cwe = rule["cwe_id"]
                    if line_no in suppressed:
                        sc = suppressed[line_no]
                        if sc is None or cwe in sc:
                            continue

                    key = f"{file_path}:{line_no}:{cwe}:{stripped}"
                    if key in seen:
                        continue
                    seen.add(key)
                    rule_counts[rule["id"]] = rule_counts.get(rule["id"], 0) + 1

                    findings.append({
                        "file_path": file_path or "unknown",
                        "line_number": line_no,
                        "cwe_id": cwe,
                        "severity": rule["severity"],
                        "title": rule["title"],
                        "explanation": rule["explanation"],
                        "code_snippet": stripped[:200],
                    })
                    break

    return findings


def scan_source_code(code: str, file_path: Optional[str] = None) -> list[dict[str, Any]]:
    """Scan raw source code string with 1-based sequential line numbering."""
    lines_with_numbers = list(enumerate(code.splitlines(keepends=False), start=1))
    return scan_diff_lines(lines_with_numbers, file_path=file_path)
