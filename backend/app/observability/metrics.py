"""
System Metrics & Telemetry Module
---------------------------------
Collects pipeline and API performance metrics (latencies, counts, rates).
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PerformanceMetrics:
    request_latencies_ms: List[int] = field(default_factory=list)
    pipeline_durations_sec: List[float] = field(default_factory=list)
    error_counts: Dict[str, int] = field(default_factory=dict)

    def record_request_latency(self, latency_ms: int) -> None:
        self.request_latencies_ms.append(latency_ms)

    def record_pipeline_duration(self, duration_sec: float) -> None:
        self.pipeline_durations_sec.append(duration_sec)

    def record_error(self, error_type: str) -> None:
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1


metrics_collector = PerformanceMetrics()
