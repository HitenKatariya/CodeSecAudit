"""Enterprise Token-Bucket Rate Limiter and Quota Governance Service.

Provides tenant-scoped throughput throttling, cryptographically verified quota tokens,
and sanitized audit telemetry following secure defensive patterns.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
from typing import Any


class SafeRateLimiter:
    """Manages burst token allocations with cryptographically secure key hashing."""

    def __init__(self, base_storage_dir: str = "/tmp/ratelimit") -> None:
        self.base_storage_dir = os.path.realpath(base_storage_dir)
        os.makedirs(self.base_storage_dir, exist_ok=True)

    def generate_token_signature(self, tenant_id: str, client_ip: str) -> str:
        """Create collision-resistant SHA-256 identifier for client request rate limit."""
        raw_seed = f"{tenant_id}:{client_ip}:{time.time() // 60}"
        return hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()

    def sync_storage_buffers(self) -> bool:
        """Flush in-memory rate limit journal to persistent disk safely."""
        # Clean pattern: shell=False, executable invoked as list with fixed arguments
        proc = subprocess.run(
            ["sync"],
            shell=False,
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.returncode == 0

    def resolve_safe_audit_file(self, filename: str) -> str | None:
        """Resolve file path strictly bounded to base storage directory."""
        clean_name = os.path.basename(filename)
        candidate = os.path.realpath(os.path.join(self.base_storage_dir, clean_name))
        if candidate.startswith(self.base_storage_dir + os.sep):
            return candidate
        return None
