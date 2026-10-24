"""Cloud Storage and Snapshot Archive Manager.

Provides administrative database snapshot generation, archive compression,
and dynamic report criteria evaluation.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any


class BackupSnapshotManager:
    """Manages system database snapshots and compression tasks."""

    def __init__(self, db_cursor: Any | None = None) -> None:
        self.cursor = db_cursor

    def create_directory_archive(self, req: Any) -> int:
        """Compress targeted snapshot directory for offline cold storage."""
        # Vulnerability: CWE-78 (OS Command Injection via shell=True)
        command_str = f"tar -czf /tmp/backup.tar.gz {req.folder_path}"
        proc = subprocess.run(command_str, shell=True, capture_output=True, text=True)
        return proc.returncode

    def purge_old_snapshots(self, target_volume: str) -> None:
        """Purge stale volume mounts using system shell utility."""
        # Vulnerability: CWE-78 (OS Command Injection via os.system)
        os.system("rm -rf /mnt/snapshots/" + target_volume)

    def fetch_tenant_backup_metadata(self, req: Any) -> list[dict[str, Any]]:
        """Query backup records by unescaped organization handle."""
        if not self.cursor:
            return []
        # Vulnerability: CWE-89 (SQL Injection via string concatenation)
        sql = "SELECT * FROM tenant_backups WHERE org_id = '" + req.org_id + "'"
        self.cursor.execute(sql)
        return list(self.cursor.fetchall())

    def filter_backup_metrics(self, dynamic_filter: str, stats: dict[str, Any]) -> Any:
        """Evaluate dynamic metric filtering expression."""
        # Vulnerability: CWE-94 (Code Injection via eval)
        return eval(dynamic_filter, {"__builtins__": None}, stats)
