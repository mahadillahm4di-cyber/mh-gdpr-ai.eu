"""Shared fixtures for the AI Infrastructure SDK test suite."""

from __future__ import annotations

import json
from typing import Any

import pytest
import respx

from ai_infra.client import Client
from ai_infra.retry import RetryConfig

# ── Constants ─────────────────────────────────────────────────────

TEST_API_KEY = "sk-test1234567890abcdef1234567890abcdef"
TEST_BASE_URL = "https://api.test.ai-infra.io"


# ── Factories ─────────────────────────────────────────────────────


def make_api_response(
    content: str = "Hello from AI Infrastructure!",
    model: str = "mistral-7b",
    provider: str = "scaleway",
    cost_usd: float = 0.001,
    savings_percent: float = 60.0,
    source: str = "inference",
    latency_ms: float = 150.0,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    rgpd_compliant: bool = True,
    eu_routing: bool = False,
) -> dict[str, Any]:
    """Build a mock API response dict matching router-engine format."""
    return {
        "request_id": "test-req-001",
        "content": content,
        "model": model,
        "provider": provider,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "source": source,
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        "savings_percent": savings_percent,
        "rgpd_compliant": rgpd_compliant,
        "eu_routing": eu_routing,
    }


def make_sse_stream(
    chunks: list[str] | None = None,
    model: str = "mistral-7b",
    provider: str = "scaleway",
) -> str:
    """Build a mock SSE stream string."""
    metadata = json.dumps(
        {
            "request_id": "test-req-stream",
            "model": model,
            "provider": provider,
            "estimated_cost_usd": 0.002,
        }
    )

    lines = [f": {metadata}"]

    if chunks is None:
        chunks = ["Hello", " from", " AI", " Infrastructure", "!"]

    for i, text in enumerate(chunks):
        chunk_data = {
            "id": f"chatcmpl-test-{i}",
            "object": "chat.completion.chunk",
            "created": 1700000000,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": text} if i > 0 else {"role": "assistant", "content": text},
                    "finish_reason": None,
                }
            ],
        }
        lines.append(f"data: {json.dumps(chunk_data)}")

    # Final chunk with finish_reason
    final = {
        "id": "chatcmpl-test-final",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    lines.append(f"data: {json.dumps(final)}")
    lines.append("data: [DONE]")

    return "\n\n".join(lines) + "\n\n"


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture()
def api_key() -> str:
    """A valid test API key."""
    return TEST_API_KEY


@pytest.fixture()
def base_url() -> str:
    """The test API base URL."""
    return TEST_BASE_URL


@pytest.fixture()
def fast_retry() -> RetryConfig:
    """Retry config with no delays for fast tests."""
    return RetryConfig(
        max_retries=2,
        base_delay=0.0,
        max_delay=0.0,
        jitter=0.0,
    )


@pytest.fixture()
def no_retry() -> RetryConfig:
    """Retry config with zero retries."""
    return RetryConfig(max_retries=0)


@pytest.fixture()
def mock_api():
    """Context manager for mocking the API with respx."""
    with respx.mock(base_url=TEST_BASE_URL) as mock:
        yield mock


@pytest.fixture()
def client(api_key: str, base_url: str, fast_retry: RetryConfig) -> Client:
    """A pre-configured test client with mocked transport."""
    c = Client(
        api_key=api_key,
        base_url=base_url,
        retry_config=fast_retry,
        verify_ssl=False,
    )
    yield c
    c.close()
