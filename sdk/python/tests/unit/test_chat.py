"""Tests for the chat completions module."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from ai_infra.client import Client
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
from ai_infra.models import ChatCompletion
from ai_infra.retry import CircuitBreakerConfig, RetryConfig
from tests.conftest import (
    TEST_API_KEY,
    TEST_BASE_URL,
    make_api_response,
    make_sse_stream,
)

ROUTE_URL = f"{TEST_BASE_URL}/v1/route"


def _make_client(**kwargs: Any) -> Client:
    """Helper to create a test client with sensible defaults."""
    defaults: dict[str, Any] = {
        "api_key": TEST_API_KEY,
        "base_url": TEST_BASE_URL,
        "verify_ssl": False,
        "retry_config": RetryConfig(max_retries=2, base_delay=0.0, max_delay=0.0, jitter=0.0),
    }
    defaults.update(kwargs)
    return Client(**defaults)


# ── Non-streaming tests ──────────────────────────────────────────

class TestChatCompletionsCreate:
    def test_basic_completion(self) -> None:
        with respx.mock:
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(),
            ))
            c = _make_client()
            result = c.chat.completions.create(
                messages=[{"role": "user", "content": "Hello"}],
            )
            assert isinstance(result, ChatCompletion)
            assert result.choices[0].message.content == "Hello from AI Infrastructure!"
            assert result.model == "mistral-7b"
            assert result.savings.cost_usd == 0.001
            c.close()

    def test_explicit_model(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(model="gpt-4o"),
            ))
            c = _make_client()
            c.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hi"}],
            )
            body = json.loads(route.calls[0].request.content)
            assert body["model"] == "gpt-4o"
            c.close()

    def test_auto_model_omits_model_field(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(),
            ))
            c = _make_client()
            c.chat.completions.create(
                model="auto",
                messages=[{"role": "user", "content": "Hi"}],
            )
            body = json.loads(route.calls[0].request.content)
            assert "model" not in body
            c.close()

    def test_routing_mode_sent(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(),
            ))
            c = _make_client()
            c.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
                routing_mode="eu_only",
            )
            body = json.loads(route.calls[0].request.content)
            assert body["routing_mode"] == "eu_only"
            c.close()

    def test_client_default_mode(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(),
            ))
            c = _make_client(mode="best_cost")
            c.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
            )
            body = json.loads(route.calls[0].request.content)
            assert body["routing_mode"] == "best_cost"
            c.close()

    def test_parameters_forwarded(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(),
            ))
            c = _make_client()
            c.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=512,
                temperature=0.3,
                top_p=0.9,
            )
            body = json.loads(route.calls[0].request.content)
            assert body["max_tokens"] == 512
            assert body["temperature"] == 0.3
            assert body["top_p"] == 0.9
            c.close()

    def test_request_id_generated(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(),
            ))
            c = _make_client()
            c.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
            )
            body = json.loads(route.calls[0].request.content)
            assert "request_id" in body
            assert len(body["request_id"]) == 36  # UUID format
            c.close()


class TestChatCompletionsValidation:
    def test_empty_messages_raises(self) -> None:
        c = _make_client()
        with pytest.raises(ValidationError, match="at least one"):
            c.chat.completions.create(messages=[])
        c.close()

    def test_invalid_role_raises(self) -> None:
        c = _make_client()
        with pytest.raises(ValidationError, match="role"):
            c.chat.completions.create(
                messages=[{"role": "god", "content": "Hi"}],
            )
        c.close()

    def test_empty_content_raises(self) -> None:
        c = _make_client()
        with pytest.raises(ValidationError, match="content"):
            c.chat.completions.create(
                messages=[{"role": "user", "content": ""}],
            )
        c.close()


class TestChatCompletionsPiiCheck:
    def test_pii_warning_emitted(self) -> None:
        with respx.mock:
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(),
            ))
            c = _make_client()
            with pytest.warns(UserWarning, match="PII detected"):
                c.chat.completions.create(
                    messages=[{"role": "user", "content": "Email: test@test.com"}],
                    pii_check=True,
                )
            c.close()

    def test_no_pii_no_warning(self) -> None:
        with respx.mock:
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(),
            ))
            c = _make_client()
            # Should not warn
            c.chat.completions.create(
                messages=[{"role": "user", "content": "What is AI?"}],
                pii_check=True,
            )
            c.close()


# ── Error handling tests ──────────────────────────────────────────

class TestChatCompletionsErrors:
    @pytest.mark.parametrize("status,exc_cls", [
        (401, AuthenticationError),
        (402, BudgetExceededError),
        (403, SecurityBlockedError),
        (429, RateLimitError),
        (503, NoProviderAvailableError),
    ])
    def test_error_mapping(self, status: int, exc_cls: type) -> None:
        with respx.mock:
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                status, text="error",
            ))
            c = _make_client(retry_config=RetryConfig(max_retries=0))
            with pytest.raises(exc_cls):
                c.chat.completions.create(
                    messages=[{"role": "user", "content": "Hi"}],
                )
            c.close()


# ── Retry tests ───────────────────────────────────────────────────

class TestChatCompletionsRetry:
    def test_retries_on_503(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(side_effect=[
                httpx.Response(503, text="Unavailable"),
                httpx.Response(503, text="Unavailable"),
                httpx.Response(200, json=make_api_response()),
            ])
            c = _make_client()
            result = c.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
            )
            assert isinstance(result, ChatCompletion)
            assert len(route.calls) == 3
            c.close()

    def test_no_retry_on_401(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                401, text="Unauthorized",
            ))
            c = _make_client()
            with pytest.raises(AuthenticationError):
                c.chat.completions.create(
                    messages=[{"role": "user", "content": "Hi"}],
                )
            assert len(route.calls) == 1
            c.close()

    def test_no_retry_on_402(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                402, text="Budget exceeded",
            ))
            c = _make_client()
            with pytest.raises(BudgetExceededError):
                c.chat.completions.create(
                    messages=[{"role": "user", "content": "Hi"}],
                )
            assert len(route.calls) == 1
            c.close()

    def test_exhausts_retries(self) -> None:
        with respx.mock:
            route = respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                503, text="Unavailable",
            ))
            c = _make_client()
            with pytest.raises(NoProviderAvailableError):
                c.chat.completions.create(
                    messages=[{"role": "user", "content": "Hi"}],
                )
            assert len(route.calls) == 3  # 1 initial + 2 retries
            c.close()


# ── Circuit breaker tests ─────────────────────────────────────────

class TestChatCompletionsCircuitBreaker:
    def test_circuit_breaker_opens(self) -> None:
        with respx.mock:
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                503, text="down",
            ))
            c = _make_client(
                retry_config=RetryConfig(max_retries=0, base_delay=0, jitter=0),
                circuit_breaker_config=CircuitBreakerConfig(failure_threshold=3),
            )

            for _ in range(3):
                with pytest.raises(NoProviderAvailableError):
                    c.chat.completions.create(
                        messages=[{"role": "user", "content": "Hi"}],
                    )

            # Circuit should now be open
            with pytest.raises(SDKConnectionError, match="Circuit breaker"):
                c.chat.completions.create(
                    messages=[{"role": "user", "content": "Hi"}],
                )
            c.close()


# ── Streaming tests ───────────────────────────────────────────────

class TestChatCompletionsStreaming:
    def test_stream_chunks(self) -> None:
        with respx.mock:
            sse_content = make_sse_stream(chunks=["Hello", " world"])
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200,
                content=sse_content.encode(),
                headers={"content-type": "text/event-stream"},
            ))
            c = _make_client()
            stream = c.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
                stream=True,
            )
            chunks = list(stream)
            # 2 content chunks + 1 finish chunk
            assert len(chunks) == 3
            assert chunks[0].choices[0].delta.content == "Hello"
            assert chunks[1].choices[0].delta.content == " world"
            assert chunks[2].choices[0].finish_reason == "stop"
            c.close()

    def test_stream_metadata(self) -> None:
        with respx.mock:
            sse_content = make_sse_stream(model="mixtral-8x7b", provider="ovhcloud")
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200,
                content=sse_content.encode(),
                headers={"content-type": "text/event-stream"},
            ))
            c = _make_client()
            stream = c.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
                stream=True,
            )
            with stream:
                _ = list(stream)
                assert stream.metadata.get("model") == "mixtral-8x7b"
                assert stream.metadata.get("provider") == "ovhcloud"
            c.close()

    def test_stream_context_manager(self) -> None:
        with respx.mock:
            sse_content = make_sse_stream()
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200,
                content=sse_content.encode(),
                headers={"content-type": "text/event-stream"},
            ))
            c = _make_client()
            stream = c.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
                stream=True,
            )
            with stream:
                chunks = list(stream)
                assert len(chunks) > 0
            c.close()

    def test_stream_error_response(self) -> None:
        with respx.mock:
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                503, text="No provider",
            ))
            c = _make_client()
            with pytest.raises(NoProviderAvailableError):
                c.chat.completions.create(
                    messages=[{"role": "user", "content": "Hi"}],
                    stream=True,
                )
            c.close()


# ── Telemetry tests ───────────────────────────────────────────────

class TestChatCompletionsTelemetry:
    def test_telemetry_recorded_on_success(self) -> None:
        with respx.mock:
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                200, json=make_api_response(cost_usd=0.005),
            ))
            c = _make_client(telemetry=True)
            c.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
            )
            stats = c.get_stats()
            assert stats["total_requests"] == 1
            assert stats["total_cost_usd"] == 0.005
            c.close()

    def test_telemetry_recorded_on_error(self) -> None:
        with respx.mock:
            respx.post(ROUTE_URL).mock(return_value=httpx.Response(
                401, text="Unauthorized",
            ))
            c = _make_client(
                telemetry=True,
                retry_config=RetryConfig(max_retries=0),
            )
            with pytest.raises(AuthenticationError):
                c.chat.completions.create(
                    messages=[{"role": "user", "content": "Hi"}],
                )
            stats = c.get_stats()
            assert stats["total_requests"] == 1
            assert stats["total_errors"] == 1
            c.close()
