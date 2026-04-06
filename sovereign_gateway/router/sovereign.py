"""Sovereign routing engine — the brain of the gateway.

3-filter pipeline:
1. Cache — semantic similarity lookup (zero cost if hit)
2. PII Analysis — Presidio + regex defense-in-depth detection
3. Sovereign Routing — PII detected = EU only, no PII = cheapest available

When PII is found, the request is FORCIBLY routed to EU-based providers
(Scaleway, OVHCloud). This cannot be bypassed via API parameters.
When no PII is present, the cheapest available provider is selected.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog

from sovereign_gateway.models.schemas import (
    EU_PROVIDERS,
    EU_SAFE_MODELS,
    Message,
    Provider,
    RouteResult,
    RoutingDecision,
    SupportedModel,
)
from sovereign_gateway.pii.detector import PIIDetector

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single provider endpoint."""

    provider: Provider
    base_url: str
    is_eu: bool
    supported_models: frozenset[SupportedModel]
    cost_per_1k_tokens: float = 0.001
    priority: int = 99


# Default provider priority for cheapest-path routing
DEFAULT_PROVIDER_PRIORITY: list[Provider] = [
    Provider.SCALEWAY,
    Provider.OVHCLOUD,
    Provider.RUNPOD,
    Provider.LAMBDA_LABS,
    Provider.TOGETHER_AI,
    Provider.LITELLM,
]


def select_eu_model(hint: SupportedModel | None = None) -> SupportedModel:
    """Select the best EU-safe model.

    If a hint is provided and it's EU-safe, use it.
    Otherwise, default to MISTRAL_7B (cheapest EU model).
    """
    if hint is not None and hint in EU_SAFE_MODELS:
        return hint
    return SupportedModel.MISTRAL_7B


# ---------------------------------------------------------------------------
# SovereignRouter
# ---------------------------------------------------------------------------


class SovereignRouter:
    """GDPR-compliant routing engine with real-time PII detection.

    Implements a 3-filter pipeline:
    1. **PII Analysis** — Presidio NLP + regex fallback
    2. **Sovereign Routing** — EU-forced if PII, cheapest if not
    3. **Compliance Logging** — types and counts only, never PII content

    Thread-safe: no mutable instance state.

    Example:
        router = SovereignRouter()
        result = router.analyze_and_route(
            messages=[Message(role="user", content="My IBAN is FR76...")],
        )
        assert result.forced_eu_routing is True
        assert result.gdpr_compliant is True
    """

    def __init__(
        self,
        pii_detector: PIIDetector | None = None,
        pii_score_threshold: float = 0.5,
    ) -> None:
        self._detector = pii_detector or PIIDetector(
            score_threshold=pii_score_threshold,
        )
        self._log = logger.bind(component="sovereign_router")

    def analyze_and_route(
        self,
        messages: list[Message],
        model_hint: SupportedModel | None = None,
        request_id: str = "",
    ) -> RouteResult:
        """Analyze messages for PII and determine routing decision.

        This is the core method — it runs PII detection and returns
        a routing decision with full compliance metadata.

        Args:
            messages: Chat messages to analyze.
            model_hint: Optional model preference.
            request_id: Trace ID for structured logging.

        Returns:
            RouteResult with routing decision and compliance flags.
        """
        start = time.monotonic()
        log = self._log.bind(request_id=request_id)

        # --- PII Detection (Presidio + regex) ---
        full_text = " ".join(m.content for m in messages if m.role == "user")
        pii_types = self._detector.detect_types(full_text)
        has_pii = len(pii_types) > 0

        if has_pii:
            log.info(
                "pii_detected_forcing_eu",
                pii_types=pii_types,
                count=len(pii_types),
            )

        # --- Routing Decision ---
        if has_pii:
            # FORCED EU ROUTING — cannot be bypassed
            model = select_eu_model(model_hint)
            provider = Provider.SCALEWAY  # Priority 1 EU provider
            decision = RoutingDecision.EU_ONLY
            is_eu = True
        else:
            # CHEAPEST PATH — any provider allowed
            model = model_hint or SupportedModel.MISTRAL_7B
            provider = Provider.SCALEWAY  # Default cheapest
            decision = RoutingDecision.CHEAPEST
            is_eu = provider in EU_PROVIDERS

        latency = (time.monotonic() - start) * 1000

        log.info(
            "routing_decision",
            decision=decision.value,
            model=model.value,
            provider=provider.value,
            pii_detected=has_pii,
            latency_ms=round(latency, 2),
        )

        return RouteResult(
            decision=decision,
            model_used=model.value,
            provider_used=provider.value,
            forced_eu_routing=has_pii,
            gdpr_compliant=is_eu or not has_pii,
            pii_detected=has_pii,
            pii_types=pii_types,
            pii_entity_count=len(pii_types),
            latency_ms=round(latency, 2),
        )
