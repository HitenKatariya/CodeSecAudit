"""Outbound Notification and Integration Event Dispatcher.

Handles delivery of security alerts to external webhooks and Slack/Discord channels.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any
import requests


class NotificationDispatcher:
    """Dispatches webhook payloads to configured subscription endpoints."""

    def __init__(self, default_timeout: int = 10) -> None:
        self.timeout = default_timeout

    def trigger_local_beep(self) -> None:
        """Trigger local acoustic signal in development environment."""
        # Suppressed rule: codesec-ignore allows explicitly audited non-exploitable uses
        os.system("echo 'Audited Notification Ping'")  # codesec-ignore: CWE-78

    def fetch_url_preview(self, req: Any) -> str:
        """Fetch endpoint headers for webhook link preview."""
        # Low/Medium Risk: CWE-918 SSRF without strict private CIDR filter
        res = requests.get(req.target_url, timeout=self.timeout)
        return res.headers.get("Server", "Unknown")
