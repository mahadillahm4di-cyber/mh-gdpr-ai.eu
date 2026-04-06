"""Tests for the retry and circuit breaker modules."""

from __future__ import annotations

import time

import pytest

from ai_infra.exceptions import (
    AuthenticationError,
    BudgetExceededError,
    NoProviderAvailableError,
    RateLimitError,
    SecurityBlockedError,
    ValidationError,
)
from ai_infra.exceptions import (
    ConnectionError as SDKConnectionError,
)
from ai_infra.exceptions import (
    TimeoutError as SDKTimeoutError,
)
from ai_infra.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
    compute_delay,
    is_retryable_exception,
    is_retryable_status,
)


class TestRetryConfig:
    def test_defaults(self) -> None:
        cfg = RetryConfig()
        assert cfg.max_retries == 3
        assert cfg.base_delay == 0.5
        assert cfg.max_delay == 30.0
        assert cfg.jitter == 0.25
        assert cfg.retry_on_timeout is True


class TestComputeDelay:
    def test_exponential_growth(self) -> None:
        cfg = RetryConfig(base_delay=1.0, jitter=0.0)
        assert compute_delay(0, cfg) == 1.0
        assert compute_delay(1, cfg) == 2.0
        assert compute_delay(2, cfg) == 4.0

    def test_capped_by_max(self) -> None:
        cfg = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=0.0)
        assert compute_delay(10, cfg) == 5.0

    def test_jitter_adds_randomness(self) -> None:
        cfg = RetryConfig(base_delay=1.0, jitter=0.5)
        delays = {compute_delay(0, cfg) for _ in range(100)}
        # With jitter, we should get varying delays
        assert len(delays) > 1


class TestIsRetryableStatus:
    @pytest.mark.parametrize("code", [429, 500, 502, 503, 504])
    def test_retryable(self, code: int) -> None:
        assert is_retryable_status(code) is True

    @pytest.mark.parametrize("code", [200, 400, 401, 402, 403, 404])
    def test_not_retryable(self, code: int) -> None:
        assert is_retryable_status(code) is False


class TestIsRetryableException:
    @pytest.mark.parametrize("exc", [
        SDKConnectionError(),
        SDKTimeoutError(),
        RateLimitError(),
        NoProviderAvailableError(),
    ])
    def test_retryable_exceptions(self, exc: Exception) -> None:
        assert is_retryable_exception(exc) is True

    @pytest.mark.parametrize("exc", [
        AuthenticationError(),
        BudgetExceededError(),
        ValidationError("bad"),
        SecurityBlockedError(),
    ])
    def test_non_retryable_exceptions(self, exc: Exception) -> None:
        assert is_retryable_exception(exc) is False


class TestCircuitBreaker:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        assert cb.allow_request() is False

    def test_stays_closed_below_threshold(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request() is True

    def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        # Should still be closed — success reset the counter
        assert cb.state == CircuitBreaker.CLOSED

    def test_transitions_to_half_open(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.01,
        ))
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

        time.sleep(0.02)
        assert cb.state == CircuitBreaker.HALF_OPEN
        assert cb.allow_request() is True

    def test_half_open_success_closes(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.01,
            success_threshold=2,
        ))
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)

        assert cb.state == CircuitBreaker.HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED

    def test_half_open_failure_reopens(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.01,
        ))
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)

        assert cb.state == CircuitBreaker.HALF_OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

    def test_reset(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2))
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

        cb.reset()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request() is True
