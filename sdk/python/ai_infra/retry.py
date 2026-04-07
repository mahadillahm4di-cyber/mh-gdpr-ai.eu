"""Retry and circuit-breaker logic for the AI Infrastructure SDK.

Implements:
- Exponential backoff with jitter for transient failures
- Client-side circuit breaker to fail fast when the API is down
- Distinguishes retryable vs non-retryable errors
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import TypeVar

import httpx

from ai_infra.exceptions import (
    AIInfraError,
    AuthenticationError,
    BudgetExceededError,
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

T = TypeVar("T")

# Status codes that should never be retried
_NON_RETRYABLE_STATUSES = frozenset({400, 401, 402, 403})

# Status codes that are always retryable
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


@dataclass
class RetryConfig:
    """Configuration for the retry strategy.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retry).
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay between retries (caps exponential growth).
        jitter: Maximum random jitter added to delay (prevents thundering herd).
        retry_on_timeout: Whether to retry on timeout errors.
    """

    max_retries: int = 3
    base_delay: float = 0.5
    max_delay: float = 30.0
    jitter: float = 0.25
    retry_on_timeout: bool = True


def compute_delay(attempt: int, config: RetryConfig) -> float:
    """Compute retry delay with exponential backoff and jitter.

    Args:
        attempt: Zero-based attempt number (0 = first retry).
        config: Retry configuration.

    Returns:
        Delay in seconds before the next attempt.
    """
    delay = min(config.base_delay * (2**attempt), config.max_delay)
    jitter = random.uniform(0, config.jitter)  # noqa: S311
    return delay + jitter


def is_retryable_status(status_code: int) -> bool:
    """Check whether an HTTP status code warrants a retry.

    Args:
        status_code: HTTP response status code.

    Returns:
        True if the status code is retryable.
    """
    return status_code in _RETRYABLE_STATUSES


def is_retryable_exception(exc: Exception) -> bool:
    """Check whether an exception warrants a retry.

    Never retries auth, budget, validation, or security errors.

    Args:
        exc: The exception to check.

    Returns:
        True if the exception is retryable.
    """
    non_retryable = (
        AuthenticationError,
        BudgetExceededError,
        ValidationError,
        SecurityBlockedError,
    )
    if isinstance(exc, non_retryable):
        return False
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, (SDKConnectionError, SDKTimeoutError)):
        return True
    if isinstance(exc, AIInfraError) and exc.status_code is not None:
        return is_retryable_status(exc.status_code)
    return isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout))


# ── Circuit Breaker ───────────────────────────────────────────────


@dataclass
class CircuitBreakerConfig:
    """Configuration for the client-side circuit breaker.

    Attributes:
        failure_threshold: Consecutive failures before opening the circuit.
        recovery_timeout: Seconds to wait before trying a half-open request.
        success_threshold: Consecutive successes in half-open to close the circuit.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    success_threshold: int = 2


class CircuitBreaker:
    """Client-side circuit breaker.

    States:
        CLOSED  — normal operation, requests go through.
        OPEN    — too many failures, requests fail immediately.
        HALF_OPEN — recovery probe: limited requests allowed.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> str:
        """Current circuit breaker state."""
        if self._state == self.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._config.recovery_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
        return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through.

        Returns:
            True if the request can proceed.
        """
        current = self.state
        return current in (self.CLOSED, self.HALF_OPEN)

    def record_success(self) -> None:
        """Record a successful request."""
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._state = self.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._success_count = 0
        if self._failure_count >= self._config.failure_threshold:
            self._state = self.OPEN
            self._last_failure_time = time.monotonic()

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
