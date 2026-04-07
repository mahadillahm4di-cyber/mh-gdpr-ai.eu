"""Exception hierarchy for the AI Infrastructure SDK.

All exceptions inherit from ``AIInfraError`` so callers can catch
a single base type.  Each subclass carries structured context
(status code, request id, provider) while *never* leaking secrets
such as API keys or internal stack traces.
"""

from __future__ import annotations


class AIInfraError(Exception):
    """Base exception for every SDK error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        super().__init__(message)

    def __repr__(self) -> str:
        parts = [f"message={self.message!r}"]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.request_id is not None:
            parts.append(f"request_id={self.request_id!r}")
        return f"{type(self).__name__}({', '.join(parts)})"


# ── Authentication ────────────────────────────────────────────────


class AuthenticationError(AIInfraError):
    """API key is invalid, expired, or missing."""

    def __init__(
        self,
        message: str = "Authentication failed — check your API key",
        **kwargs: object,
    ) -> None:
        super().__init__(message, status_code=401, **kwargs)  # type: ignore[arg-type]


class PermissionError(AIInfraError):  # noqa: A001 – shadows builtin intentionally for DX
    """Tenant lacks the required scope or is suspended."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        **kwargs: object,
    ) -> None:
        super().__init__(message, status_code=403, **kwargs)  # type: ignore[arg-type]


# ── Rate limiting / budget ────────────────────────────────────────


class RateLimitError(AIInfraError):
    """Too many requests — the caller should slow down."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: float | None = None,
        **kwargs: object,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, status_code=429, **kwargs)  # type: ignore[arg-type]


class BudgetExceededError(AIInfraError):
    """Monthly budget for the tenant tier has been exhausted."""

    def __init__(
        self,
        message: str = "Budget exceeded for your tier",
        **kwargs: object,
    ) -> None:
        super().__init__(message, status_code=402, **kwargs)  # type: ignore[arg-type]


# ── Provider / routing ────────────────────────────────────────────


class ProviderError(AIInfraError):
    """Upstream GPU provider returned an error."""

    def __init__(
        self,
        message: str = "Provider error",
        *,
        provider: str | None = None,
        **kwargs: object,
    ) -> None:
        self.provider = provider
        super().__init__(message, status_code=502, **kwargs)  # type: ignore[arg-type]


class NoProviderAvailableError(AIInfraError):
    """No provider could serve the request after all fallbacks."""

    def __init__(
        self,
        message: str = "No provider available — try again later",
        **kwargs: object,
    ) -> None:
        super().__init__(message, status_code=503, **kwargs)  # type: ignore[arg-type]


# ── Validation ────────────────────────────────────────────────────


class ValidationError(AIInfraError):
    """Client-side request validation failed before sending."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, status_code=400, **kwargs)  # type: ignore[arg-type]


# ── Security ──────────────────────────────────────────────────────


class SecurityBlockedError(AIInfraError):
    """Request was blocked by the security screening layer."""

    def __init__(
        self,
        message: str = "Request blocked by security screening",
        **kwargs: object,
    ) -> None:
        super().__init__(message, status_code=403, **kwargs)  # type: ignore[arg-type]


# ── Network ───────────────────────────────────────────────────────


class ConnectionError(AIInfraError):  # noqa: A001
    """Network-level failure (DNS, TCP, TLS handshake)."""

    def __init__(
        self,
        message: str = "Connection failed — check your network",
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]


class TimeoutError(AIInfraError):  # noqa: A001
    """Request exceeded the configured timeout."""

    def __init__(
        self,
        message: str = "Request timed out",
        *,
        timeout_seconds: float | None = None,
        **kwargs: object,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message, **kwargs)  # type: ignore[arg-type]


# ── Mapping helper ────────────────────────────────────────────────

_STATUS_MAP: dict[int, type[AIInfraError]] = {
    401: AuthenticationError,
    402: BudgetExceededError,
    403: SecurityBlockedError,
    429: RateLimitError,
    502: ProviderError,
    503: NoProviderAvailableError,
}


_MAX_ERROR_BODY_LENGTH = 500

# Generic messages for auth errors — never echo server body for 401/403
_SAFE_MESSAGES: dict[int, str] = {
    401: "Authentication failed — check your API key",
    403: "Request blocked — insufficient permissions",
}


def from_status_code(
    status_code: int,
    body: str,
    *,
    request_id: str | None = None,
) -> AIInfraError:
    """Create the correct exception from an HTTP status code.

    Auth error bodies are replaced with generic messages to prevent
    accidental leakage of API keys or internal data through error
    logging in calling applications.
    """
    exc_cls = _STATUS_MAP.get(status_code, AIInfraError)
    safe_body = _SAFE_MESSAGES.get(status_code, body[:_MAX_ERROR_BODY_LENGTH])
    return exc_cls(
        message=safe_body,
        request_id=request_id,
    )
