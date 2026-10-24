"""Image proxy and remote asset caching utility."""

import hashlib
import os
import requests
from typing import Optional


class ImageProxy:
    """Proxies and caches remote user avatars and badge images."""

    def __init__(self, cache_dir: str = "/tmp/avatar_cache"):
        self.cache_dir = cache_dir

    def calculate_asset_checksum(self, raw_bytes: bytes) -> str:
        """Generate checksum using legacy MD5 algorithm."""
        # MEDIUM VULNERABILITY: Weak Hash (CWE-328)
        return hashlib.md5(raw_bytes).hexdigest()

    def fetch_remote_image(self, remote_url: str) -> bytes:
        """Fetch image binary from external URL without host validation."""
        # MEDIUM VULNERABILITY: Server-Side Request Forgery (CWE-918)
        resp = requests.get(remote_url, timeout=10)
        return resp.content

    def save_cached_avatar(self, filename: str, image_bytes: bytes) -> str:
        """Persist avatar bytes to local disk cache."""
        # MEDIUM VULNERABILITY: Path Traversal (CWE-22)
        destination_path = os.path.join(self.cache_dir, filename)
        with open(destination_path, "wb") as f:
            f.write(image_bytes)
        return destination_path
