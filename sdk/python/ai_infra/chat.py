"""Chat completions interface — OpenAI-compatible.

Provides ``ChatCompletions.create()`` with identical signature to
``openai.chat.completions.create()``, returning either a full
``ChatCompletion`` or a streaming iterator of ``ChatCompletionChunk``.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

import httpx

from ai_infra.exceptions import (
    ConnectionError as SDKConnectionError,
)
from ai_infra.exceptions import (
    TimeoutError as SDKTimeoutError,
)
from ai_infra.exceptions import (
    from_status_code,
)
from ai_infra.models import (
    ChatCompletion,
    ChatCompletionChunk,
    RoutingMode,
)
from ai_infra.retry import (
    compute_delay,
    is_retryable_exception,
)
from ai_infra.security import detect_pii, validate_messages
from ai_infra.telemetry import RequestMetrics, TelemetryCollector

if TYPE_CHECKING:
    from ai_infra.client import Client


class ChatCompletions:
    """Chat completions resource — mirrors ``openai.chat.completions``.

    Args:
        client: Parent Client instance (provides http_client, config, etc.).
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    def create(
        self,
        *,
        model: str = "auto",
        messages: list[dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stream: bool = False,
        routing_mode: str | RoutingMode | None = None,
        pii_check: bool = False,
        **kwargs: Any,
    ) -> ChatCompletion | StreamIterator:
        """Create a chat completion.

        Fully compatible with the OpenAI ``chat.completions.create()``
        signature.  Extra parameters (``routing_mode``, ``pii_check``)
        are platform extensions.

        Args:
            model: Model identifier or ``"auto"`` for intelligent routing.
            messages: List of message dicts (``role`` + ``content``).
            max_tokens: Maximum tokens in the completion.
            temperature: Sampling temperature (0.0 - 2.0).
            top_p: Nucleus sampling parameter (0.0 - 1.0).
            stream: If True, return a streaming iterator.
            routing_mode: Override the client's default routing mode.
            pii_check: If True, warn when PII is detected client-side.
            **kwargs: Extra parameters forwarded to the API.

        Returns:
            ``ChatCompletion`` (non-streaming) or ``StreamIterator`` (streaming).

        Raises:
            AIInfraError: On any API or network error.
        """
        validated = validate_messages(messages)

        if pii_check:
            for msg in validated:
                pii_found = detect_pii(msg["content"])
                if pii_found:
                    import warnings
                    warnings.warn(
                        f"PII detected client-side: {pii_found}. "
                        f"Server will route to EU providers for RGPD compliance.",
                        UserWarning,
                        stacklevel=2,
                    )
                    break

        mode = routing_mode or self._client.routing_mode
        if isinstance(mode, RoutingMode):
            mode = mode.value

        body: dict[str, Any] = {
            "messages": validated,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
            "request_id": str(uuid.uuid4()),
        }

        if model != "auto":
            body["model"] = model

        if mode:
            body["routing_mode"] = mode

        if stream:
            return self._create_stream(body)

        return self._create_sync(body)

    def _create_sync(self, body: dict[str, Any]) -> ChatCompletion:
        """Execute a non-streaming chat completion with retry.

        Args:
            body: Request body dict.

        Returns:
            Parsed ChatCompletion.
        """
        cfg = self._client.retry_config
        cb = self._client.circuit_breaker
        last_exc: Exception | None = None

        for attempt in range(cfg.max_retries + 1):
            if not cb.allow_request():
                raise SDKConnectionError(
                    "Circuit breaker is open — API appears unavailable. "
                    "Retrying automatically after recovery timeout.",
                )

            t0 = time.monotonic()
            try:
                response = self._client.http_client.post(
                    self._client.route_url,
                    json=body,
                    headers=self._client.auth_headers,
                )
                elapsed_ms = (time.monotonic() - t0) * 1000

                if response.status_code == 200:
                    cb.record_success()
                    data = response.json()
                    result = ChatCompletion.from_api_response(data)
                    self._record_telemetry(result, elapsed_ms, 200)
                    return result

                exc = from_status_code(
                    response.status_code,
                    response.text,
                    request_id=body.get("request_id"),
                )
                cb.record_failure()

                if not is_retryable_exception(exc) or attempt >= cfg.max_retries:
                    self._record_telemetry(None, elapsed_ms, response.status_code)
                    raise exc

                last_exc = exc

            except httpx.TimeoutException:
                elapsed_ms = (time.monotonic() - t0) * 1000
                cb.record_failure()
                exc = SDKTimeoutError(
                    timeout_seconds=self._client.timeout,
                    request_id=body.get("request_id"),
                )
                if not cfg.retry_on_timeout or attempt >= cfg.max_retries:
                    self._record_telemetry(None, elapsed_ms, 0)
                    raise exc from None
                last_exc = exc

            except httpx.ConnectError as e:
                elapsed_ms = (time.monotonic() - t0) * 1000
                cb.record_failure()
                exc = SDKConnectionError(str(e), request_id=body.get("request_id"))
                if attempt >= cfg.max_retries:
                    self._record_telemetry(None, elapsed_ms, 0)
                    raise exc from None
                last_exc = exc

            delay = compute_delay(attempt, cfg)
            time.sleep(delay)

        if last_exc is not None:
            raise last_exc
        raise SDKConnectionError("Unexpected retry loop exit")  # pragma: no cover

    def _create_stream(self, body: dict[str, Any]) -> StreamIterator:
        """Start a streaming chat completion (no retry — streams are not retryable).

        Args:
            body: Request body dict.

        Returns:
            StreamIterator yielding ChatCompletionChunk objects.
        """
        cb = self._client.circuit_breaker
        if not cb.allow_request():
            raise SDKConnectionError(
                "Circuit breaker is open — API appears unavailable.",
            )

        try:
            response = self._client.http_client.send(
                self._client.http_client.build_request(
                    "POST",
                    self._client.route_url,
                    json=body,
                    headers=self._client.auth_headers,
                ),
                stream=True,
            )
        except httpx.TimeoutException:
            cb.record_failure()
            raise SDKTimeoutError(
                timeout_seconds=self._client.timeout,
                request_id=body.get("request_id"),
            ) from None
        except httpx.ConnectError as e:
            cb.record_failure()
            raise SDKConnectionError(
                str(e), request_id=body.get("request_id"),
            ) from None

        if response.status_code != 200:
            body_text = response.read().decode()
            response.close()
            cb.record_failure()
            raise from_status_code(
                response.status_code,
                body_text,
                request_id=body.get("request_id"),
            )

        cb.record_success()
        return StreamIterator(
            response=response,
            telemetry=self._client.telemetry,
            request_id=body.get("request_id", ""),
        )

    def _record_telemetry(
        self,
        result: ChatCompletion | None,
        latency_ms: float,
        status_code: int,
    ) -> None:
        """Record request metrics to the telemetry collector.

        Args:
            result: The completion result (None on error).
            latency_ms: End-to-end latency.
            status_code: HTTP status code.
        """
        self._client.telemetry.record(
            RequestMetrics(
                model=result.model if result else "",
                latency_ms=latency_ms,
                status_code=status_code,
                is_stream=False,
                is_cache_hit=(
                    result.savings.source == "cache" if result else False
                ),
                cost_usd=result.savings.cost_usd if result else 0.0,
                savings_usd=result.savings.cost_saved_usd if result else 0.0,
            ),
        )


class StreamIterator:
    """Iterator over SSE streaming chunks.

    Parses the server-sent events stream into ``ChatCompletionChunk``
    objects.  Supports both ``for chunk in stream`` and context manager
    usage.

    The first SSE comment (prefixed with ``:``) contains routing metadata
    (model, provider, cost estimate) which is exposed via ``metadata``.
    """

    def __init__(
        self,
        response: httpx.Response,
        telemetry: TelemetryCollector,
        request_id: str = "",
    ) -> None:
        self._response = response
        self._telemetry = telemetry
        self._request_id = request_id
        self._metadata: dict[str, Any] = {}
        self._closed = False
        self._t0 = time.monotonic()

    @property
    def metadata(self) -> dict[str, Any]:
        """Routing metadata from the SSE comment header."""
        return self._metadata

    def __iter__(self) -> Iterator[ChatCompletionChunk]:
        """Iterate over streaming chunks."""
        try:
            yield from self._iter_chunks()
        finally:
            self.close()

    def _iter_chunks(self) -> Iterator[ChatCompletionChunk]:
        """Parse the SSE stream into ChatCompletionChunk objects."""
        for line in self._response.iter_lines():
            line = line.strip()

            if not line:
                continue

            # SSE comment — routing metadata
            if line.startswith(":"):
                comment = line[1:].strip()
                try:  # noqa: SIM105
                    self._metadata = json.loads(comment)
                except (json.JSONDecodeError, ValueError):
                    pass
                continue

            # SSE data line
            if line.startswith("data:"):
                data_str = line[5:].strip()

                if data_str == "[DONE]":
                    elapsed_ms = (time.monotonic() - self._t0) * 1000
                    self._telemetry.record(
                        RequestMetrics(
                            model=self._metadata.get("model", ""),
                            latency_ms=elapsed_ms,
                            status_code=200,
                            is_stream=True,
                            cost_usd=self._metadata.get("estimated_cost_usd", 0.0),
                        ),
                    )
                    return

                try:
                    data = json.loads(data_str)
                    yield ChatCompletionChunk.from_sse_data(data)
                except (json.JSONDecodeError, ValueError):
                    continue

    def close(self) -> None:
        """Close the underlying HTTP response."""
        if not self._closed:
            self._response.close()
            self._closed = True

    def __enter__(self) -> StreamIterator:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class Chat:
    """Namespace for chat resources — mirrors ``openai.chat``.

    Args:
        client: Parent Client instance.
    """

    def __init__(self, client: Client) -> None:
        self.completions = ChatCompletions(client)
