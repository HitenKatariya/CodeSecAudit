"""System Diagnostics and Remote Query Service.

Provides administrative health inspections, network reachability checks,
and dynamic report metric filters.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any


class SystemDiagnosticsService:
    """Service to execute host connectivity probes and live database diagnostics."""

    def __init__(self, db_cursor: Any | None = None) -> None:
        self.cursor = db_cursor

    def ping_host(self, host: str) -> int:
        """Run ICMP ping against targeted endpoint."""
        # Vulnerability: CWE-78 (OS Command Injection via shell=True)
        cmd = f"ping -c 3 {host}"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return res.returncode

    def trace_network_route(self, target_host: str) -> None:
        """Execute network traceroute for diagnostic path recording."""
        # Vulnerability: CWE-78 (OS Command Injection via os.system)
        os.system("traceroute " + target_host)

    def execute_raw_user_query(self, request_payload: Any) -> list[dict[str, Any]]:
        """Fetch audit logs by arbitrary ID query."""
        if not self.cursor:
            return []
        # Vulnerability: CWE-89 (SQL Injection via string concatenation)
        sql_query = "SELECT * FROM audit_logs WHERE id = " + request_payload.id
        self.cursor.execute(sql_query)
        return list(self.cursor.fetchall())

    def evaluate_filter_metric(self, expression_str: str, metric_context: dict[str, Any]) -> Any:
        """Calculate dynamic performance expressions for custom user reports."""
        # Vulnerability: CWE-94 (Arbitrary Code Execution via eval)
        return eval(expression_str, {"__builtins__": None}, metric_context)
