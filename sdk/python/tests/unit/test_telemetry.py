"""Tests for the telemetry module."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from ai_infra.telemetry import RequestMetrics, TelemetryCollector


class TestRequestMetrics:
    def test_defaults(self) -> None:
        m = RequestMetrics(model="test", latency_ms=100, status_code=200)
        assert m.is_stream is False
        assert m.is_cache_hit is False
        assert m.cost_usd == 0.0
        assert m.savings_usd == 0.0


class TestTelemetryCollector:
    def test_disabled_by_default(self) -> None:
        t = TelemetryCollector()
        assert t.enabled is False

    def test_enabled_explicit(self) -> None:
        t = TelemetryCollector(enabled=True)
        assert t.enabled is True

    @pytest.mark.parametrize("env_val", ["1", "true", "yes", "True", "YES"])
    def test_enabled_by_env(self, env_val: str) -> None:
        with patch.dict(os.environ, {"AI_INFRA_TELEMETRY": env_val}):
            t = TelemetryCollector()
            assert t.enabled is True

    def test_disabled_noop(self) -> None:
        t = TelemetryCollector(enabled=False)
        t.record(RequestMetrics(model="m", latency_ms=100, status_code=200))
        stats = t.get_stats()
        assert stats["total_requests"] == 0

    def test_records_success(self) -> None:
        t = TelemetryCollector(enabled=True)
        t.record(
            RequestMetrics(
                model="mistral-7b",
                latency_ms=150,
                status_code=200,
                cost_usd=0.001,
                savings_usd=0.002,
            )
        )
        stats = t.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_errors"] == 0
        assert stats["avg_latency_ms"] == 150.0
        assert stats["total_cost_usd"] == 0.001
        assert stats["total_savings_usd"] == 0.002

    def test_records_errors(self) -> None:
        t = TelemetryCollector(enabled=True)
        t.record(
            RequestMetrics(
                model="m",
                latency_ms=100,
                status_code=500,
            )
        )
        stats = t.get_stats()
        assert stats["total_errors"] == 1
        assert stats["error_rate"] == 1.0

    def test_records_cache_hits(self) -> None:
        t = TelemetryCollector(enabled=True)
        t.record(
            RequestMetrics(
                model="m",
                latency_ms=10,
                status_code=200,
                is_cache_hit=True,
            )
        )
        stats = t.get_stats()
        assert stats["cache_hit_rate"] == 1.0

    def test_records_streams(self) -> None:
        t = TelemetryCollector(enabled=True)
        t.record(
            RequestMetrics(
                model="m",
                latency_ms=200,
                status_code=200,
                is_stream=True,
            )
        )
        stats = t.get_stats()
        assert stats["stream_rate"] == 1.0

    def test_aggregate_multiple(self) -> None:
        t = TelemetryCollector(enabled=True)
        for i in range(5):
            t.record(
                RequestMetrics(
                    model="m",
                    latency_ms=100.0 * (i + 1),
                    status_code=200,
                    cost_usd=0.001,
                )
            )
        stats = t.get_stats()
        assert stats["total_requests"] == 5
        assert stats["avg_latency_ms"] == 300.0  # (100+200+300+400+500)/5
        assert stats["total_cost_usd"] == 0.005

    def test_callback_invoked(self) -> None:
        callback = MagicMock()
        t = TelemetryCollector(enabled=True, on_request=callback)
        m = RequestMetrics(model="m", latency_ms=50, status_code=200)
        t.record(m)
        callback.assert_called_once_with(m)

    def test_callback_not_invoked_when_disabled(self) -> None:
        callback = MagicMock()
        t = TelemetryCollector(enabled=False, on_request=callback)
        t.record(RequestMetrics(model="m", latency_ms=50, status_code=200))
        callback.assert_not_called()

    def test_reset(self) -> None:
        t = TelemetryCollector(enabled=True)
        t.record(RequestMetrics(model="m", latency_ms=100, status_code=200))
        t.reset()
        stats = t.get_stats()
        assert stats["total_requests"] == 0
