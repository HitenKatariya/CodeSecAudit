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
            r"(?:SELECT|INSERT|UPDATE|DELETE)\s+.*?\+\s*[A-Za-z0-9_.]+",
            r"(?:db|cursor|conn|session)?\.?execute\s*\(\s*['\"].*?['\"]\s*\+",
            r"(?:db|cursor|conn|session)?\.?query\s*\(\s*['\"].*?['\"]\s*\+",
            r"(?:db|cursor|conn|session)?\.?execute\s*\(\s*f['\"].*?\{.*?\}",
            r"(?:db|cursor|conn|session)?\.?query\s*\(\s*f['\"].*?\{.*?\}",
            r"(?:SELECT|INSERT|UPDATE|DELETE).*?f['\"].*?\{.*?\}",
            r"(?:SELECT|INSERT|UPDATE|DELETE).*?\.format\s*\(",
            r"(?:db|cursor|conn|session)?\.?execute\s*\(\s*['\"][^'\"]*?%s[^'\"]*?['\"]\s*%",
        ],
        "explanation": "Building SQL queries with string concatenation allows SQL injection.",
    },
    {
        "id": "subprocess-shell",
        "title": "OS Command Injection via subprocess/shell",
        "cwe_id": "CWE-78",
        "severity": "critical",
        "patterns": [
            r"subprocess\.(?:call|Popen|run|check_output|check_call)\s*\(.*?shell\s*=\s*True",
            r"subprocess\.(?:call|Popen|run|check_output|check_call)\s*\(",
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


def _parse_suppressed_cwes(line: str, tag: str) -> Optional[set[str]]:
    """Parse suppressed CWEs after tag ('codesec-ignore-next-line' or 'codesec-ignore').
    
    Returns a set of uppercase CWE IDs (e.g. {'CWE-89'}),
    or None if all findings should be suppressed on target line (wildcard / CWE-XXX).
    """
    pattern = rf"{tag}\s*(?::\s*([^\n\r]+))?"
    m = re.search(pattern, line, re.IGNORECASE)
    if not m or not m.group(1):
        return None  # No colon or empty -> suppress all
    rest = m.group(1).strip()
    if not rest or "cwe-xxx" in rest.lower() or "all" in rest.lower():
        return None  # Wildcard CWE-XXX or all -> suppress all
    cwes = {c.upper() for c in re.findall(r"CWE-\d+", rest, re.IGNORECASE)}
    return cwes if cwes else None


def _is_parameterized_query(line: str) -> bool:
    """Detect whether a query line uses safe parameterization or prepared statements.
    
    Checks for:
    1. Parameters passed as tuple, dict, or list argument to execute/query methods:
       e.g. db.execute(sql, (param,)), db.execute(sql, {"param": ...}), cursor.execute(..., [...])
    2. Presence of query parameter placeholders (%s, ?, :param, $1) combined with query execution
    """
    # 1. Check for execute/query calls with parameterized arguments (tuple, dict, list, or params var)
    # e.g. db.execute(sql, {"id": user_id}), cursor.execute(sql, (param,)), db.execute(sql, [param])
    exec_param_pattern = r"(?:execute|query|executemany)\s*\([^,]+,\s*(?:\{|\(|\[|dict\b|tuple\b|list\b|[A-Za-z_]\w*)"
    if re.search(exec_param_pattern, line):
        # Ensure it's not simply string concat where 2nd arg doesn't exist
        # Check if there is an actual parameter argument
        if re.search(r"(?:execute|query|executemany)\s*\([^,]+,\s*(?:\{.*?\}|\(.*?\)|\[.*?\]|dict\(|tuple\(|list\(|[A-Za-z_]\w*\s*\))", line):
            return True

    # 2. Check for parameter placeholders like %s, ?, :param, $1 inside SQL strings
    # But ensure % is not being used as Python string formatting operator (% var)
    has_named_param = bool(re.search(r"['\"][^'\"]*:[a-zA-Z_]\w*[^'\"]*['\"]", line))
    has_qmark = bool(re.search(r"['\"][^'\"]*\?[^'\"]*['\"]", line))
    has_dollar_param = bool(re.search(r"['\"][^'\"]*\$\d+[^'\"]*['\"]", line))
    has_percent_s = bool(re.search(r"['\"][^'\"]*%s[^'\"]*['\"]", line))
    is_percent_formatting = bool(re.search(r"['\"][^'\"]*%s[^'\"]*['\"]\s*%", line))

    if (has_named_param or has_qmark or has_dollar_param or (has_percent_s and not is_percent_formatting)):
        # If placeholders exist and query is parameterized or passed to execute/query with parameters
        if re.search(r"(?:execute|query)\s*\(.+?,\s*(?:\{|\(|\[|[A-Za-z_]\w*)", line):
            return True

    return False


def _is_safe_command(line: str) -> bool:
    """Detect whether a command execution line uses safe arguments.
    
    Checks for:
    1. Safe arguments when shlex.quote(...) is used
    2. Safe arguments when a list without shell=True is used
    """
    if "shlex.quote(" in line:
        return True

    has_shell_true = bool(re.search(r"shell\s*=\s*True", line, re.IGNORECASE))
    if not has_shell_true:
        # Check if subprocess is called with a list argument: subprocess.run([...])
        if re.search(r"subprocess\.(?:call|Popen|run|check_output|check_call)\s*\(\s*\[", line):
            return True
        # Or explicitly shell=False
        if re.search(r"subprocess\.(?:call|Popen|run|check_output|check_call)\s*\(", line) and re.search(r"shell\s*=\s*False", line, re.IGNORECASE):
            return True

    return False


def _build_suppression_map(lines: list[str]) -> dict[int, Optional[set[str]]]:
    suppressed: dict[int, Optional[set[str]]] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if "codesec-ignore-next-line" in stripped:
            cwes = _parse_suppressed_cwes(stripped, "codesec-ignore-next-line")
            target_line = i + 2
            if cwes is None:
                suppressed[target_line] = None
            else:
                existing = suppressed.get(target_line)
                if existing is not None:
                    existing.update(cwes)
                elif target_line not in suppressed:
                    suppressed[target_line] = set(cwes)
        elif "codesec-ignore" in stripped:
            cwes = _parse_suppressed_cwes(stripped, "codesec-ignore")
            target_line = i + 1
            if cwes is None:
                suppressed[target_line] = None
            else:
                existing = suppressed.get(target_line)
                if existing is not None:
                    existing.update(cwes)
                elif target_line not in suppressed:
                    suppressed[target_line] = set(cwes)
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
            cwes = _parse_suppressed_cwes(stripped, "codesec-ignore-next-line")
            next_line_no = lines_with_numbers[idx + 1][0] if idx + 1 < len(lines_with_numbers) else line_no + 1
            if cwes is None:
                suppressed[next_line_no] = None
            else:
                existing = suppressed.get(next_line_no)
                if existing is not None:
                    existing.update(cwes)
                elif next_line_no not in suppressed:
                    suppressed[next_line_no] = set(cwes)
        elif "codesec-ignore" in stripped:
            cwes = _parse_suppressed_cwes(stripped, "codesec-ignore")
            if cwes is None:
                suppressed[line_no] = None
            else:
                existing = suppressed.get(line_no)
                if existing is not None:
                    existing.update(cwes)
                elif line_no not in suppressed:
                    suppressed[line_no] = set(cwes)

    for line_no, line in lines_with_numbers:
        if len(findings) >= MAX_TOTAL_FINDINGS:
            break
        stripped = line.strip()
        if not stripped:
            continue

        # Skip comment lines
        if stripped.startswith(("#", "//", "/*", "*")):
            continue

        for rule in RULES:
            if len(findings) >= MAX_TOTAL_FINDINGS or rule_counts.get(rule["id"], 0) >= MAX_FINDINGS_PER_RULE:
                continue

            for pattern in rule["patterns"]:
                if re.search(pattern, stripped, re.IGNORECASE):
                    cwe = rule["cwe_id"]

                    # Check developer inline suppression
                    if line_no in suppressed:
                        sc = suppressed[line_no]
                        if sc is None or cwe in sc:
                            continue

                    # Check false-positive suppression for SQL Injection (CWE-89)
                    if cwe == "CWE-89" and _is_parameterized_query(stripped):
                        continue

                    # Check false-positive suppression for Command Injection (CWE-78)
                    if cwe == "CWE-78" and _is_safe_command(stripped):
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
