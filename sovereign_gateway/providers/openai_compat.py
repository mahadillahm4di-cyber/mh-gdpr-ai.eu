"""OpenAI-compatible provider client.

Calls any LLM API that implements the OpenAI chat completions format.
This covers: Scaleway, OVHcloud, Together AI, Mistral, OpenAI, DeepSeek,
Groq, Fireworks, and any other OpenAI-compatible endpoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Default model names per provider (what the API actually expects)
_PROVIDER_MODEL_MAP: dict[str, dict[str, str]] = {
    "scaleway": {
        "mistral-7b": "mistral-7b-instruct-v0.3",
        "mixtral-8x7b": "mixtral-8x7b-instruct-v0.1",
        "codestral": "codestral-mamba-7b-v0.1",
        "mistral-large": "mistral-large-latest",
        "llama-3-8b": "meta-llama-3-8b-instruct",
        "llama-3-70b": "meta-llama-3-70b-instruct",
    },
    "ovhcloud": {
        "mistral-7b": "mistral-7b-instruct-v0.3",
        "mixtral-8x7b": "mixtral-8x7b-instruct-v0.1",
        "llama-3-8b": "meta-llama-3-8b-instruct",
        "llama-3-70b": "meta-llama-3-70b-instruct",
    },
    "together_ai": {
        "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3",
        "mixtral-8x7b": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "llama-3-8b": "meta-llama/Meta-Llama-3-8B-Instruct",
        "llama-3-70b": "meta-llama/Meta-Llama-3-70B-Instruct",
        "deepseek-v2": "deepseek-ai/DeepSeek-V2-Chat",
        "deepseek-coder": "deepseek-ai/DeepSeek-Coder-V2-Instruct",
    },
    "openai": {
        "gpt-4o": "gpt-4o",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
    },
}

# Default base URLs per provider
_PROVIDER_BASE_URLS: dict[str, str] = {
    "scaleway": "https://api.scaleway.ai/v1",
    "ovhcloud": "https://ai.ovhcloud.com/v1",
    "together_ai": "https://api.together.xyz/v1",
    "openai": "https://api.openai.com/v1",
    "runpod": "https://api.runpod.ai/v2",
    "litellm": "http://localhost:4000",
}

# Environment variable names for API keys
_PROVIDER_ENV_KEYS: dict[str, str] = {
    "scaleway": "SCALEWAY_API_KEY",
    "ovhcloud": "OVHCLOUD_API_KEY",
    "together_ai": "TOGETHER_AI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "runpod": "RUNPOD_API_KEY",
    "lambda_labs": "LAMBDA_LABS_API_KEY",
    "litellm": "LITELLM_API_KEY",
}


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single provider."""

    name: str
    api_key: str
    base_url: str
    is_eu: bool = False
    priority: int = 99
    timeout: float = 30.0


def _resolve_api_model(provider_name: str, model_id: str) -> str:
    """Resolve our model ID to the provider's actual model name."""
    provider_map = _PROVIDER_MODEL_MAP.get(provider_name, {})
    return provider_map.get(model_id, model_id)


class OpenAICompatClient:
    """HTTP client for OpenAI-compatible LLM APIs.

    Supports any provider that implements the /v1/chat/completions endpoint.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout
        self._log = logger.bind(component="provider_client")

    def call(
        self,
        config: ProviderConfig,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Call an OpenAI-compatible chat completions endpoint.

        Args:
            config: Provider configuration with API key and base URL.
            model: Model ID (our internal name, auto-resolved to provider name).
            messages: Chat messages in OpenAI format.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            Raw API response as dict.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses.
            httpx.ConnectError: On connection failure.
        """
        api_model = _resolve_api_model(config.name, model)
        url = f"{config.base_url.rstrip('/')}/chat/completions"

        payload = {
            "model": api_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        self._log.info(
            "provider_call",
            provider=config.name,
            model=api_model,
            url=url,
        )

        with httpx.Client(timeout=config.timeout) as client:
            response = client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result


def load_providers_from_env() -> dict[str, ProviderConfig]:
    """Load provider configs from environment variables.

    Reads SCALEWAY_API_KEY, TOGETHER_AI_API_KEY, etc.

    Returns:
        Dict of provider name -> ProviderConfig for all configured providers.
    """
    providers: dict[str, ProviderConfig] = {}

    eu_providers = {"scaleway", "ovhcloud"}
    priorities = {
        "scaleway": 1,
        "ovhcloud": 2,
        "runpod": 3,
        "lambda_labs": 4,
        "together_ai": 5,
        "openai": 6,
        "litellm": 7,
    }

    for name, env_key in _PROVIDER_ENV_KEYS.items():
        api_key = os.environ.get(env_key, "")
        if not api_key or api_key == "CHANGE_ME":
            continue

        base_url = os.environ.get(
            f"{name.upper()}_BASE_URL",
            _PROVIDER_BASE_URLS.get(name, ""),
        )
        if not base_url:
            continue

        providers[name] = ProviderConfig(
            name=name,
            api_key=api_key,
            base_url=base_url,
            is_eu=name in eu_providers,
            priority=priorities.get(name, 99),
        )

    if providers:
        logger.info(
            "providers_loaded",
            count=len(providers),
            names=sorted(providers.keys()),
        )

    return providers
