"""Pydantic models for the mh-gdpr-ai.eu.

All data flowing through the gateway is validated through these models.
No raw dicts — every boundary uses a typed Pydantic model.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Provider(str, enum.Enum):
    """Supported infrastructure providers, ordered by priority."""

    SCALEWAY = "scaleway"
    OVHCLOUD = "ovhcloud"
    RUNPOD = "runpod"
    LAMBDA_LABS = "lambda_labs"
    TOGETHER_AI = "together_ai"
    LITELLM = "litellm"


class SupportedModel(str, enum.Enum):
    """Supported model identifiers across all providers."""

    # Mistral (EU-safe)
    MISTRAL_7B = "mistral-7b"
    MIXTRAL_8X7B = "mixtral-8x7b"
    CODESTRAL = "codestral"
    MISTRAL_LARGE = "mistral-large"
    MISTRAL_EMBED = "mistral-embed"

    # Meta / Llama (EU-safe when hosted on EU providers)
    LLAMA_3_70B = "llama-3-70b"
    LLAMA_3_8B = "llama-3-8b"

    # Google (EU-safe when hosted on EU providers)
    GEMMA_7B = "gemma-7b"

    # OpenAI (non-EU, used only when no PII detected)
    GPT_4O = "gpt-4o"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_35_TURBO = "gpt-3.5-turbo"

    # Anthropic (non-EU)
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"

    # Google (non-EU)
    GEMINI_PRO = "gemini-pro"

    # Cohere
    COMMAND_R_PLUS = "command-r-plus"
    COMMAND_R = "command-r"

    # DeepSeek
    DEEPSEEK_V2 = "deepseek-v2"
    DEEPSEEK_CODER = "deepseek-coder"


class RoutingDecision(str, enum.Enum):
    """Routing decision type."""

    EU_ONLY = "eu_only"
    CHEAPEST = "cheapest"
    CACHE_HIT = "cache_hit"


# Models safe for EU-only routing (can be hosted on EU providers)
EU_SAFE_MODELS: frozenset[SupportedModel] = frozenset({
    SupportedModel.MISTRAL_7B,
    SupportedModel.MIXTRAL_8X7B,
    SupportedModel.CODESTRAL,
    SupportedModel.MISTRAL_LARGE,
    SupportedModel.MISTRAL_EMBED,
    SupportedModel.LLAMA_3_70B,
    SupportedModel.LLAMA_3_8B,
    SupportedModel.GEMMA_7B,
})

# EU-based providers (GDPR-compliant hosting)
EU_PROVIDERS: frozenset[Provider] = frozenset({
    Provider.SCALEWAY,
    Provider.OVHCLOUD,
})


# ---------------------------------------------------------------------------
# PII
# ---------------------------------------------------------------------------


class PIIEntity(BaseModel):
    """A detected PII entity in the text."""

    entity_type: str = Field(..., description="Type of PII (e.g., EMAIL_ADDRESS, PERSON)")
    start: int = Field(..., ge=0, description="Start character index")
    end: int = Field(..., ge=0, description="End character index")
    score: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    source: str = Field(default="regex", description="Detection source: presidio or regex")


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


class Message(BaseModel):
    """A single message in a chat conversation."""

    role: str = Field(..., pattern=r"^(system|user|assistant)$", description="Message role")
    content: str = Field(..., min_length=1, max_length=1_000_000, description="Message content")


# ---------------------------------------------------------------------------
# Route result
# ---------------------------------------------------------------------------


class RouteResult(BaseModel):
    """Complete result of a sovereign routing decision.

    Contains routing metadata, PII detection results, and compliance flags.
    This is the main output of the gateway — everything a compliance officer needs.
    """

    decision: RoutingDecision = Field(..., description="Routing decision type")
    model_used: str = Field(..., description="Model that processed the request")
    provider_used: str = Field(..., description="Provider that served the request")
    forced_eu_routing: bool = Field(..., description="Whether EU routing was forced due to PII")
    gdpr_compliant: bool = Field(..., description="Whether the request is GDPR compliant")
    pii_detected: bool = Field(..., description="Whether PII was found in the input")
    pii_types: list[str] = Field(default_factory=list, description="Types of PII detected")
    pii_entity_count: int = Field(default=0, ge=0, description="Number of PII entities found")
    latency_ms: float = Field(..., ge=0.0, description="Total processing latency in ms")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Inference cost in USD")
    cached: bool = Field(default=False, description="Whether response came from cache")

    @property
    def compliance_summary(self) -> dict[str, Any]:
        """Generate a compliance-ready summary for audit logs."""
        return {
            "gdpr_compliant": self.gdpr_compliant,
            "pii_detected": self.pii_detected,
            "pii_types": self.pii_types,
            "routing_decision": self.decision.value,
            "provider_region": "EU" if self.forced_eu_routing else "ANY",
            "provider": self.provider_used,
            "model": self.model_used,
        }
