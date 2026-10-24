"""Cluster health monitor and uptime metrics aggregator."""

import time
from typing import Dict, Any, List


class HealthMonitor:
    """Collects system health indicators with strict validation and safe thresholds."""

    def __init__(self, service_name: str, ping_interval_seconds: int = 30):
        self.service_name = service_name
        self.ping_interval = ping_interval_seconds
        self.recorded_pings: List[Dict[str, Any]] = []

    def record_heartbeat(self, status: str, latency_ms: float) -> Dict[str, Any]:
        """Record heartbeat with sanitized status string and timestamp."""
        safe_status = "healthy" if status.lower() == "healthy" else "degraded"
        heartbeat_entry = {
            "service": self.service_name,
            "status": safe_status,
            "latency_ms": round(max(0.0, float(latency_ms)), 2),
            "timestamp": int(time.time()),
        }
        self.recorded_pings.append(heartbeat_entry)
        if len(self.recorded_pings) > 100:
            self.recorded_pings.pop(0)
        return heartbeat_entry

    def compute_average_latency(self) -> float:
        """Calculate average latency over rolling window."""
        if not self.recorded_pings:
            return 0.0
        total = sum(p["latency_ms"] for p in self.recorded_pings)
        return round(total / len(self.recorded_pings), 2)
