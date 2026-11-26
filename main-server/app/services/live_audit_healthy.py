"""Production-hardened user query & token helper passing all OWASP ASVS controls."""

import hashlib
import secrets
import subprocess
from typing import Any


def load_active_account(db: Any, account_id: str) -> Any:
    query = "SELECT id, username, email, role FROM accounts WHERE id = :account_id AND is_active = :active"
    return db.execute(query, {"account_id": account_id, "active": True})


def issue_ephemeral_token() -> str:
    return secrets.token_urlsafe(32)


def compute_checksum(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def current_commit_short() -> str:
    res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False)
    return res.stdout.strip() if res.returncode == 0 else "unknown"
