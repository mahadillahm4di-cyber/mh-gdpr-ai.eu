"""Pydantic response models — OpenAI-compatible structure.

These models mirror the OpenAI API response format so that existing
code using ``openai.ChatCompletion`` can switch to this SDK with
zero changes beyond the client instantiation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ── Enums ─────────────────────────────────────────────────────────

class RoutingMode(str, Enum):
    """Available routing optimization modes."""

    BEST_COST = "best_cost"
    BEST_QUALITY = "best_quality"
    BEST_SPEED = "best_speed"
    BALANCED = "balanced"
    BEST_AVAILABILITY = "best_availability"
    EU_ONLY = "eu_only"


class RouteSource(str, Enum):
    """Whether the response came from inference or cache."""

    INFERENCE = "inference"
    CACHE = "cache"


# ── Usage ─────────────────────────────────────────────────────────

class Usage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


# ── Savings (platform-specific extension) ─────────────────────────

class Savings(BaseModel):
    """Cost and sovereignty information attached to each response.

    This is the key differentiator: every response tells the client
    exactly how much they saved compared to retail pricing.
    """

    # Idea 1 — Cost savings
    cost_usd: float = Field(0.0, description="Actual cost in USD")
    cost_saved_usd: float = Field(0.0, description="Savings vs retail pricing in USD")
    savings_percent: float = Field(0.0, description="Savings percentage (0-100)")
    model_used: str = Field("", description="Model that served the request")
    provider_used: str = Field("", description="Provider that served the request")
    source: str = Field("inference", description="'inference' or 'cache'")
    cache_hit: bool = Field(False, description="Whether the response came from semantic cache")
    latency_ms: float = Field(0.0, description="Server-side latency in milliseconds")

    # Idea 2 — Sovereign AI Gateway
    rgpd_compliant: bool = Field(True, description="Whether routing was RGPD-compliant")
    eu_routing: bool = Field(False, description="Whether EU-only routing was used")
    forced_eu_routing: bool = Field(
        False, description="Whether EU routing was forced due to PII detection",
    )
    pii_types_detected: list[str] = Field(
        default_factory=list, description="PII types detected server-side",
    )


# ── Chat completion (non-streaming) ───────────────────────────────

class Choice(BaseModel):
    """A single completion choice."""

    index: int = 0
    message: ChoiceMessage
    finish_reason: str | None = "stop"


class ChoiceMessage(BaseModel):
    """Message within a choice (non-streaming)."""

    role: str = "assistant"
    content: str = ""


class ChatCompletion(BaseModel):
    """Full chat completion response — OpenAI-compatible.

    Extended with ``savings`` field for cost transparency.
    """

    id: str = ""
    object: str = "chat.completion"
    created: int = 0
    model: str = ""
    choices: list[Choice] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    savings: Savings = Field(default_factory=Savings)
    request_id: str = ""

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> ChatCompletion:
        """Build a ChatCompletion from the router-engine JSON response.

        Args:
            data: Raw JSON response dict from the API.

        Returns:
            Populated ChatCompletion instance.
        """
        return cls(
            id=f"chatcmpl-{data.get('request_id', '')}",
            object="chat.completion",
            created=0,
            model=data.get("model", ""),
            choices=[
                Choice(
                    index=0,
                    message=ChoiceMessage(
                        role="assistant",
                        content=data.get("content", ""),
                    ),
                    finish_reason="stop",
                ),
            ],
            usage=Usage(
                prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
                total_tokens=data.get("usage", {}).get("total_tokens", 0),
            ),
            savings=Savings(
                # Idea 1 — Cost savings
                cost_usd=data.get("cost_usd", 0.0),
                cost_saved_usd=data.get("savings_percent", 0.0) * data.get("cost_usd", 0.0) / 100.0,
                savings_percent=data.get("savings_percent", 0.0),
                model_used=data.get("model", ""),
                provider_used=data.get("provider", ""),
                source=data.get("source", "inference"),
                cache_hit=data.get("source", "inference") == "cache",
                latency_ms=data.get("latency_ms", 0.0),
                # Idea 2 — Sovereign AI Gateway
                rgpd_compliant=data.get("rgpd_compliant", True),
                eu_routing=data.get("eu_routing", False),
                forced_eu_routing=data.get("forced_eu_routing", data.get("eu_routing", False)),
                pii_types_detected=data.get("pii_types_detected", []),
            ),
            request_id=data.get("request_id", ""),
        )


# ── Streaming chunks ─────────────────────────────────────────────

class DeltaContent(BaseModel):
    """Delta content within a streaming chunk."""

    role: str | None = None
    content: str | None = None


class StreamChoice(BaseModel):
    """A single choice within a streaming chunk."""

    index: int = 0
    delta: DeltaContent = Field(default_factory=DeltaContent)
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    """Single streaming chunk — OpenAI-compatible."""

    id: str = ""
    object: str = "chat.completion.chunk"
    created: int = 0
    model: str = ""
    choices: list[StreamChoice] = Field(default_factory=list)

    @classmethod
    def from_sse_data(cls, data: dict[str, Any]) -> ChatCompletionChunk:
        """Build a chunk from parsed SSE JSON.

        Args:
            data: Parsed JSON from an SSE ``data:`` line.

        Returns:
            Populated ChatCompletionChunk instance.
        """
        choices_raw = data.get("choices", [])
        choices = []
        for c in choices_raw:
            delta_raw = c.get("delta", {})
            choices.append(
                StreamChoice(
                    index=c.get("index", 0),
                    delta=DeltaContent(
                        role=delta_raw.get("role"),
                        content=delta_raw.get("content"),
                    ),
                    finish_reason=c.get("finish_reason"),
                ),
            )

        return cls(
            id=data.get("id", ""),
            object=data.get("object", "chat.completion.chunk"),
            created=data.get("created", 0),
            model=data.get("model", ""),
            choices=choices,
        )


# ── Model listing ─────────────────────────────────────────────────

class ModelInfo(BaseModel):
    """Information about a single available model."""

    id: str
    object: str = "model"
    owned_by: str = "ai-infra"
    capabilities: list[str] = Field(default_factory=list)
    eu_safe: bool = False


class ModelList(BaseModel):
    """List of available models — OpenAI /v1/models compatible."""

    object: str = "list"
    data: list[ModelInfo] = Field(default_factory=list)


# Statically known model catalog (matches router-engine catalog)
AVAILABLE_MODELS: list[ModelInfo] = [
    ModelInfo(id="mistral-7b", capabilities=["chat"], eu_safe=True),
    ModelInfo(id="mixtral-8x7b", capabilities=["chat", "reasoning"], eu_safe=True),
    ModelInfo(id="codestral", capabilities=["code"], eu_safe=True),
    ModelInfo(id="mistral-large", capabilities=["chat", "reasoning"], eu_safe=True),
    ModelInfo(id="mistral-embed", capabilities=["embeddings"], eu_safe=True),
    ModelInfo(id="llama-3-70b", capabilities=["chat", "reasoning"], eu_safe=True),
    ModelInfo(id="llama-3-8b", capabilities=["chat"], eu_safe=True),
    ModelInfo(id="gemma-7b", capabilities=["chat"], eu_safe=True),
    ModelInfo(id="gpt-4o", capabilities=["chat", "reasoning"]),
    ModelInfo(id="gpt-4-turbo", capabilities=["chat", "reasoning"]),
    ModelInfo(id="gpt-3.5-turbo", capabilities=["chat"]),
    ModelInfo(id="claude-3-opus", capabilities=["chat", "reasoning"]),
    ModelInfo(id="claude-3-sonnet", capabilities=["chat", "reasoning"]),
    ModelInfo(id="claude-3-haiku", capabilities=["chat"]),
    ModelInfo(id="codellama-34b", capabilities=["code"], eu_safe=True),
    ModelInfo(id="gemini-pro", capabilities=["chat", "reasoning"]),
    ModelInfo(id="command-r-plus", capabilities=["chat", "reasoning"]),
    ModelInfo(id="command-r", capabilities=["chat"]),
    ModelInfo(id="phi-3-medium", capabilities=["chat"]),
    ModelInfo(id="phi-3-mini", capabilities=["chat"]),
    ModelInfo(id="deepseek-v2", capabilities=["chat", "reasoning"]),
    ModelInfo(id="deepseek-coder", capabilities=["code"]),
    ModelInfo(id="qwen2-72b", capabilities=["chat", "reasoning"]),
    ModelInfo(id="qwen2-7b", capabilities=["chat"]),
]
