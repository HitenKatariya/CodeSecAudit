"""Telemetry metrics collector for CodeSecAudit runtime events."""

import time
from typing import Any, Dict

class TelemetryCollector:
    """Collects in-memory latency and throughput counters for audit jobs."""

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self._latencies: Dict[str, list[float]] = {}

    def increment(self, metric_name: str, count: int = 1) -> None:
        """Increment a named telemetry metric counter."""
        self._counters[metric_name] = self._counters.get(metric_name, 0) + count

    def record_latency(self, metric_name: str, duration_seconds: float) -> None:
        """Record the execution duration of an audited event."""
        if metric_name not in self._latencies:
            self._latencies[metric_name] = []
        self._latencies[metric_name].append(duration_seconds)

    def get_summary(self) -> Dict[str, Any]:
        """Return a structured dictionary snapshot of all current metrics."""
        return {
            "timestamp": time.time(),
            "counters": dict(self._counters),
            "latencies": {k: (sum(v) / len(v) if v else 0.0) for k, v in self._latencies.items()},
        }
