"""Tests for the exception hierarchy."""

from __future__ import annotations

import pytest

from ai_infra.exceptions import (
    AIInfraError,
    AuthenticationError,
    BudgetExceededError,
    NoProviderAvailableError,
    ProviderError,
    RateLimitError,
    SecurityBlockedError,
    ValidationError,
    from_status_code,
)
from ai_infra.exceptions import (
    ConnectionError as SDKConnectionError,
)
from ai_infra.exceptions import (
    PermissionError as SDKPermissionError,
)
from ai_infra.exceptions import (
    TimeoutError as SDKTimeoutError,
)


class TestAIInfraError:
    def test_base_error_attributes(self) -> None:
        exc = AIInfraError("test", status_code=500, request_id="req-1")
        assert exc.message == "test"
        assert exc.status_code == 500
        assert exc.request_id == "req-1"
        assert str(exc) == "test"

    def test_base_error_repr(self) -> None:
        exc = AIInfraError("fail", status_code=400, request_id="r1")
        r = repr(exc)
        assert "AIInfraError" in r
        assert "fail" in r
        assert "400" in r
        assert "r1" in r

    def test_base_error_optional_fields(self) -> None:
        exc = AIInfraError("simple")
        assert exc.status_code is None
        assert exc.request_id is None


class TestSpecificExceptions:
    def test_authentication_error_defaults(self) -> None:
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert "API key" in exc.message

    def test_permission_error(self) -> None:
        exc = SDKPermissionError()
        assert exc.status_code == 403

    def test_rate_limit_with_retry_after(self) -> None:
        exc = RateLimitError(retry_after=30.0)
        assert exc.status_code == 429
        assert exc.retry_after == 30.0

    def test_budget_exceeded(self) -> None:
        exc = BudgetExceededError()
        assert exc.status_code == 402

    def test_provider_error_with_provider(self) -> None:
        exc = ProviderError(provider="scaleway")
        assert exc.provider == "scaleway"
        assert exc.status_code == 502

    def test_no_provider_available(self) -> None:
        exc = NoProviderAvailableError()
        assert exc.status_code == 503

    def test_security_blocked(self) -> None:
        exc = SecurityBlockedError()
        assert exc.status_code == 403

    def test_validation_error(self) -> None:
        exc = ValidationError("bad input")
        assert exc.status_code == 400
        assert exc.message == "bad input"

    def test_connection_error(self) -> None:
        exc = SDKConnectionError()
        assert "network" in exc.message.lower()

    def test_timeout_error(self) -> None:
        exc = SDKTimeoutError(timeout_seconds=5.0)
        assert exc.timeout_seconds == 5.0


class TestInheritance:
    @pytest.mark.parametrize(
        "exc_cls,kwargs",
        [
            (AuthenticationError, {}),
            (SDKPermissionError, {}),
            (RateLimitError, {}),
            (BudgetExceededError, {}),
            (ProviderError, {}),
            (NoProviderAvailableError, {}),
            (ValidationError, {"message": "bad"}),
            (SecurityBlockedError, {}),
            (SDKConnectionError, {}),
            (SDKTimeoutError, {}),
        ],
    )
    def test_all_inherit_from_base(self, exc_cls: type, kwargs: dict) -> None:
        exc = exc_cls(**kwargs)
        assert isinstance(exc, AIInfraError)

    def test_catchable_with_base(self) -> None:
        with pytest.raises(AIInfraError):
            raise AuthenticationError()


class TestFromStatusCode:
    @pytest.mark.parametrize(
        "code,expected_cls",
        [
            (401, AuthenticationError),
            (402, BudgetExceededError),
            (403, SecurityBlockedError),
            (429, RateLimitError),
            (502, ProviderError),
            (503, NoProviderAvailableError),
        ],
    )
    def test_maps_status_codes(self, code: int, expected_cls: type) -> None:
        exc = from_status_code(code, "error body", request_id="req-1")
        assert isinstance(exc, expected_cls)
        assert exc.request_id == "req-1"

    def test_unknown_status_falls_back(self) -> None:
        exc = from_status_code(418, "teapot")
        assert isinstance(exc, AIInfraError)
        assert exc.message == "teapot"
