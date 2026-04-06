"""Main client for the AI Infrastructure SDK.

Drop-in replacement for ``openai.OpenAI()`` — same interface,
30-70% lower costs, RGPD-compliant routing, built-in savings tracking.

Usage::

    from ai_infra import Client

    client = Client(api_key="sk-...")
    response = client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": "Hello"}],
    )
    print(response.choices[0].message.content)
    print(response.savings.cost_saved_usd)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import httpx

from ai_infra.chat import Chat
from ai_infra.models import (
    AVAILABLE_MODELS,
    ModelInfo,
    ModelList,
    RoutingMode,
)
from ai_infra.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
)
from ai_infra.security import mask_api_key, resolve_api_key
from ai_infra.telemetry import RequestMetrics, TelemetryCollector

# Default API base URL
_DEFAULT_BASE_URL = "https://api.ai-infra.io"

# Routing mode aliases for convenience
_MODE_ALIASES: dict[str, str] = {
    "best_quality": RoutingMode.BEST_QUALITY.value,
    "best_cost": RoutingMode.BEST_COST.value,
    "best_speed": RoutingMode.BEST_SPEED.value,
    "balanced": RoutingMode.BALANCED.value,
    "eu_only": RoutingMode.EU_ONLY.value,
    "best_availability": RoutingMode.BEST_AVAILABILITY.value,
}


class Client:
    """AI Infrastructure SDK client.

    Compatible with the OpenAI client interface.  Accepts the same
    ``base_url`` and ``api_key`` parameters so existing code can
    switch by changing a single import.

    Args:
        api_key: API key (``sk-...``).  Falls back to ``AI_INFRA_API_KEY`` env var.
        base_url: API base URL.  Defaults to ``https://api.ai-infra.io``.
        mode: Default routing mode (``best_cost``, ``best_quality``,
            ``best_speed``, ``balanced``, ``eu_only``).
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts for transient errors.
        telemetry: Enable local telemetry collection.
        on_request: Callback invoked after each completed request.
        verify_ssl: Verify server TLS certificates (always True in production).
        proxy: HTTP/SOCKS proxy URL for all requests.
        ca_bundle: Path to a custom CA certificate bundle.
        circuit_breaker_config: Override circuit breaker settings.
        retry_config: Override retry settings.

    Example::

        # Minimal
        client = Client(api_key="sk-...")

        # With mode
        client = Client(api_key="sk-...", mode="eu_only")

        # From environment
        import os
        os.environ["AI_INFRA_API_KEY"] = "sk-..."
        client = Client()
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        mode: str | RoutingMode | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        telemetry: bool = False,
        on_request: Callable[[RequestMetrics], Any] | None = None,
        verify_ssl: bool = True,
        proxy: str | None = None,
        ca_bundle: str | None = None,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        # Resolve and validate API key
        self._api_key = resolve_api_key(api_key)
        self._masked_key = mask_api_key(self._api_key)

        # Base URL (strip trailing slash)
        self._base_url = base_url.rstrip("/")

        # Routing mode
        if isinstance(mode, RoutingMode):
            self._routing_mode = mode.value
        elif isinstance(mode, str):
            self._routing_mode = _MODE_ALIASES.get(mode, mode)
        else:
            self._routing_mode = None

        # Timeouts
        self._timeout = timeout

        # Retry configuration
        self._retry_config = retry_config or RetryConfig(max_retries=max_retries)

        # Circuit breaker
        self._circuit_breaker = CircuitBreaker(circuit_breaker_config)

        # Telemetry
        self._telemetry = TelemetryCollector(
            enabled=telemetry,
            on_request=on_request,
        )

        # HTTP client — single persistent connection pool
        transport_kwargs: dict[str, Any] = {}
        if proxy:
            transport_kwargs["proxy"] = proxy

        self._http_client = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            verify=ca_bundle if ca_bundle else verify_ssl,
            headers={
                "User-Agent": "ai-infra-python/1.0.0",
                "Accept": "application/json",
            },
            # Never follow redirects — prevents API key leak to redirect targets
            follow_redirects=False,
            **transport_kwargs,
        )

        # Resources (OpenAI-compatible namespace)
        self.chat = Chat(self)

    # ── Properties ────────────────────────────────────────────────

    @property
    def route_url(self) -> str:
        """Full URL for the route endpoint."""
        return f"{self._base_url}/v1/route"

    @property
    def auth_headers(self) -> dict[str, str]:
        """Authorization headers for API requests.

        The API key is sent as a Bearer token for JWT-based auth,
        and also as X-API-Key for direct key validation.
        """
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
        }

    @property
    def routing_mode(self) -> str | None:
        """Default routing mode."""
        return self._routing_mode

    @property
    def timeout(self) -> float:
        """Request timeout in seconds."""
        return self._timeout

    @property
    def retry_config(self) -> RetryConfig:
        """Retry configuration."""
        return self._retry_config

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Client-side circuit breaker."""
        return self._circuit_breaker

    @property
    def http_client(self) -> httpx.Client:
        """Underlying HTTP client."""
        return self._http_client

    @property
    def telemetry(self) -> TelemetryCollector:
        """Telemetry collector."""
        return self._telemetry

    # ── Model listing ─────────────────────────────────────────────

    def list_models(self) -> ModelList:
        """List all available models.

        Returns:
            ModelList with all supported models and their capabilities.
        """
        return ModelList(data=AVAILABLE_MODELS)

    def get_model(self, model_id: str) -> ModelInfo | None:
        """Get information about a specific model.

        Args:
            model_id: The model identifier.

        Returns:
            ModelInfo if found, None otherwise.
        """
        for m in AVAILABLE_MODELS:
            if m.id == model_id:
                return m
        return None

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, float]:
        """Get local telemetry statistics.

        Returns:
            Dictionary with aggregate request stats.
        """
        return self._telemetry.get_stats()

    # ── Lifecycle ─────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http_client.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"Client(base_url={self._base_url!r}, "
            f"api_key={self._masked_key!r}, "
            f"mode={self._routing_mode!r})"
        )
