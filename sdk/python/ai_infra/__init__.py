"""AI Infrastructure Python SDK.

Drop-in replacement for the OpenAI client with 30-70% cost savings,
RGPD-compliant routing, and real-time savings tracking.

Quick start::

    from ai_infra import Client

    client = Client(api_key="sk-...")
    response = client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    print(response.choices[0].message.content)
    print(f"Saved: ${response.savings.cost_saved_usd:.4f}")
"""

from ai_infra.client import Client
from ai_infra.exceptions import (
    AIInfraError,
    AuthenticationError,
    BudgetExceededError,
    ConnectionError,  # noqa: A004
    NoProviderAvailableError,
    PermissionError,  # noqa: A004
    ProviderError,
    RateLimitError,
    SecurityBlockedError,
    TimeoutError,  # noqa: A004
    ValidationError,
)
from ai_infra.models import (
    AVAILABLE_MODELS,
    ChatCompletion,
    ChatCompletionChunk,
    ModelInfo,
    ModelList,
    RoutingMode,
    Savings,
    Usage,
)

__version__ = "1.0.0"

__all__ = [
    # Client
    "Client",
    # Models
    "ChatCompletion",
    "ChatCompletionChunk",
    "ModelInfo",
    "ModelList",
    "RoutingMode",
    "Savings",
    "Usage",
    "AVAILABLE_MODELS",
    # Exceptions
    "AIInfraError",
    "AuthenticationError",
    "BudgetExceededError",
    "ConnectionError",
    "NoProviderAvailableError",
    "PermissionError",
    "ProviderError",
    "RateLimitError",
    "SecurityBlockedError",
    "TimeoutError",
    "ValidationError",
]
