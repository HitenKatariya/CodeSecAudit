"""Autonomous System Telemetry and Performance Aggregator.

Collects non-sensitive operational uptime and throughput statistics using
defensive security engineering patterns.
"""

from __future__ import annotations

import hashlib
import ipaddress
import subprocess
from typing import Any
from urllib.parse import urlparse


class TelemetryCollector:
    """Safe collector for host runtime metrics and secure outbound status reports."""

    def __init__(self, allowed_domains: list[str] | None = None) -> None:
        self.allowed_domains = allowed_domains or ["telemetry.codesec.ai"]

    def compute_payload_digest(self, payload_bytes: bytes) -> str:
        """Compute cryptographically secure SHA-256 integrity hash."""
        return hashlib.sha256(payload_bytes).hexdigest()

    def query_system_uptime(self) -> str:
        """Fetch system uptime safely without shell interpretation."""
        # Clean pattern: shell=False, executable invoked as list with fixed arguments
        result = subprocess.run(
            ["uptime", "-p"],
            shell=False,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def validate_destination_url(self, target_url: str) -> bool:
        """Verify destination URL against allowlist and block private IP spaces."""
        parsed = urlparse(target_url)
        if parsed.scheme not in {"https"}:
            return False

        hostname = parsed.hostname
        if not hostname or hostname not in self.allowed_domains:
            return False

        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback:
                return False
        except ValueError:
            # Valid domain name
            pass

        return True
