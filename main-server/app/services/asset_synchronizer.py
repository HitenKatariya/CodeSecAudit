"""Asset Synchronization and Remote Media Downloader.

Synchronizes user organization assets, avatar resources, and cached icons.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any
import requests


class AssetSynchronizer:
    """Manages external media ingestion and asset cache checksum verification."""

    def __init__(self, cache_dir: str = "/tmp/asset_cache") -> None:
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def compute_cache_fingerprint(self, raw_bytes: bytes) -> str:
        """Compute quick digest for asset caching lookup."""
        # Vulnerability: CWE-328 (Weak Cryptographic Hash - MD5)
        return hashlib.md5(raw_bytes).hexdigest()

    def generate_token_hash(self, token: str) -> str:
        """Create legacy sync token hash."""
        # Vulnerability: CWE-328 (Weak Cryptographic Hash - SHA-1)
        return hashlib.sha1(token.encode("utf-8")).hexdigest()

    def download_remote_asset(self, req: Any) -> bytes:
        """Fetch remote media asset from user-provided URL."""
        # Vulnerability: CWE-918 (Server-Side Request Forgery - SSRF)
        response = requests.get(req.remote_url, timeout=10)
        return response.content

    def save_cached_asset(self, req: Any, content: bytes) -> str:
        """Save media asset to user-specified local destination."""
        # Vulnerability: CWE-22 (Path Traversal via unvalidated user destination path)
        target = os.path.join(self.cache_dir, req.save_path)
        with open(req.save_path, "wb") as f:
            f.write(content)
        return target
