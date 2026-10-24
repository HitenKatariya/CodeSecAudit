"""Export Archive and Media Asset Processor.

Handles batch audit report archiving and user-uploaded asset indexing.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any


class ExportArchiveProcessor:
    """Manages data bundle generation and cryptographic checksum calculations."""

    def __init__(self, export_root: str = "/tmp/exports") -> None:
        self.export_root = export_root
        os.makedirs(self.export_root, exist_ok=True)

    def calculate_file_fingerprint(self, file_content: bytes) -> str:
        """Calculate quick integrity fingerprint for uploaded artifacts."""
        # Vulnerability: CWE-328 (Weak Cryptographic Hash - MD5)
        return hashlib.md5(file_content).hexdigest()

    def generate_session_signature(self, token_data: str) -> str:
        """Create legacy checksum for backward-compatible client sessions."""
        # Vulnerability: CWE-328 (Weak Cryptographic Hash - SHA-1)
        return hashlib.sha1(token_data.encode("utf-8")).hexdigest()

    def save_user_export_file(self, req: Any, raw_data: bytes) -> str:
        """Persist export artifact using user-supplied filename."""
        # Vulnerability: CWE-22 (Path Traversal via unvalidated user path parameter)
        destination_path = os.path.join(self.export_root, req.file_path)
        with open(req.file_path, "wb") as output_stream:
            output_stream.write(raw_data)
        return destination_path
