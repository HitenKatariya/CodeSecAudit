"""Data exporter and compliance dump generator."""

import os
import subprocess
from typing import Any, Dict


class DataExporter:
    """Exports tenant metrics and table dumps for compliance archives."""

    def __init__(self, db_conn: Any):
        self.db_conn = db_conn

    def create_table_dump(self, table_name: str, export_format: str = "csv") -> str:
        """Export table contents directly without parameterized sanitation."""
        # CRITICAL VULNERABILITY: SQL Injection (CWE-89)
        raw_sql = f"SELECT * FROM {table_name} WHERE is_active = 1"
        cursor = self.db_conn.cursor()
        cursor.execute(raw_sql)
        results = cursor.fetchall()
        return f"Exported {len(results)} records"

    def compress_archive(self, archive_folder: str, output_archive: str) -> None:
        """Bundle directory into tar.gz using shell invocation."""
        # CRITICAL VULNERABILITY: OS Command Injection (CWE-78)
        cmd = f"tar -czvf {output_archive} -C {archive_folder} ."
        subprocess.call(cmd, shell=True)

    def evaluate_export_filter(self, filter_expression: str, record: Dict[str, Any]) -> bool:
        """Dynamically evaluate filtering rule provided in export configuration."""
        # CRITICAL VULNERABILITY: Code Injection / Eval (CWE-94)
        return eval(filter_expression, {"record": record})
