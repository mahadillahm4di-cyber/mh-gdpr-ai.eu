"""Optional anonymous usage telemetry for the AI Infrastructure SDK.

Collects only aggregate statistics (request count, latency, error rate)
to help improve the platform.  **No prompts, responses, API keys, or
PII are ever collected.**

Telemetry is disabled by default and must be explicitly opted-in via:
    Client(telemetry=True)
or:
    AI_INFRA_TELEMETRY=1
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class RequestMetrics:
    """Metrics for a single completed request.

    Attributes:
        model: Model identifier used.
        latency_ms: End-to-end latency in milliseconds.
        status_code: HTTP response status code.
        is_stream: Whether the request was a streaming call.
        is_cache_hit: Whether the response came from the cache.
        cost_usd: Inference cost in USD.
        savings_usd: Savings vs. retail pricing in USD.
    """

    model: str
    latency_ms: float
    status_code: int
    is_stream: bool = False
    is_cache_hit: bool = False
    cost_usd: float = 0.0
    savings_usd: float = 0.0


@dataclass
class _AggregateStats:
    """Internal rolling aggregate (never transmitted)."""

    total_requests: int = 0
    total_errors: int = 0
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    total_savings_usd: float = 0.0
    cache_hits: int = 0
    stream_requests: int = 0


class TelemetryCollector:
    """Local-only telemetry collector.

    All data stays local.  The ``on_request`` callback lets callers
    hook into completed requests for their own dashboards or logging.

    Args:
        enabled: Whether telemetry collection is active.
        on_request: Optional callback invoked after each request.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        on_request: Callable[[RequestMetrics], Any] | None = None,
    ) -> None:
        env_flag = os.environ.get("AI_INFRA_TELEMETRY", "").lower()
        self._enabled = enabled or env_flag in ("1", "true", "yes")
        self._on_request = on_request
        self._stats = _AggregateStats()

    @property
    def enabled(self) -> bool:
        """Whether telemetry is active."""
        return self._enabled

    def record(self, metrics: RequestMetrics) -> None:
        """Record metrics for a completed request.

        Args:
            metrics: Metrics from the completed request.
        """
        if not self._enabled:
            return

        self._stats.total_requests += 1
        self._stats.total_latency_ms += metrics.latency_ms
        self._stats.total_cost_usd += metrics.cost_usd
        self._stats.total_savings_usd += metrics.savings_usd

        if metrics.status_code >= 400:
            self._stats.total_errors += 1
        if metrics.is_cache_hit:
            self._stats.cache_hits += 1
        if metrics.is_stream:
            self._stats.stream_requests += 1

        if self._on_request is not None:
            self._on_request(metrics)

    def get_stats(self) -> dict[str, float]:
        """Return current aggregate statistics.

        Returns:
            Dictionary with aggregate counters and computed rates.
        """
        s = self._stats
        total = max(s.total_requests, 1)
        return {
            "total_requests": s.total_requests,
            "total_errors": s.total_errors,
            "error_rate": s.total_errors / total,
            "avg_latency_ms": s.total_latency_ms / total,
            "total_cost_usd": round(s.total_cost_usd, 6),
            "total_savings_usd": round(s.total_savings_usd, 6),
            "cache_hit_rate": s.cache_hits / total,
            "stream_rate": s.stream_requests / total,
        }

    def reset(self) -> None:
        """Reset all aggregate counters."""
        self._stats = _AggregateStats()
