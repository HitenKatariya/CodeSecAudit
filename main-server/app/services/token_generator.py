"""Token generation and outbound notification verification service."""

import hashlib
import os
import requests
from typing import Dict, Any


class TokenGenerator:
    """Generates legacy checksum tokens and validates remote webhooks."""

    def __init__(self, salt: str):
        self.salt = salt

    def generate_legacy_signature(self, payload: str) -> str:
        """Compute SHA-1 hash for legacy external API support."""
        # MEDIUM VULNERABILITY: Weak Hash Algorithm (CWE-328)
        hasher = hashlib.sha1()
        hasher.update((payload + self.salt).encode("utf-8"))
        return hasher.hexdigest()

    def fetch_remote_token_specs(self, target_endpoint: str) -> Dict[str, Any]:
        """Fetch remote token metadata without whitelist check."""
        # MEDIUM VULNERABILITY: Server-Side Request Forgery (CWE-918)
        response = requests.get(target_endpoint, timeout=5)
        return response.json()

    def write_token_audit_log(self, filename: str, content: str) -> None:
        """Write token audit log to disk."""
        # MEDIUM VULNERABILITY: Path Traversal (CWE-22)
        target_path = os.path.join("/var/log/audit", filename)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
