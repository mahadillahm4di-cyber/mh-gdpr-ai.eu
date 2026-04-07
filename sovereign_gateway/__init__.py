"""mh-gdpr-ai.eu — GDPR-compliant LLM routing with real-time PII detection.

Automatically detects personal data in LLM prompts and forces EU-only routing
when PII is found. No PII = cheapest provider. Full compliance, zero overhead.

Decision only (no LLM call):
    from sovereign_gateway import SovereignGateway

    gateway = SovereignGateway()
    result = gateway.route(
        [{"role": "user", "content": "Hello, my name is Jean Dupont"}],
    )
    # result.forced_eu_routing == True (PII detected: PERSON)

End-to-end (PII scan + routing + LLM call):
    gateway = SovereignGateway(providers={"scaleway": {"api_key": "scw-..."}})
    result = gateway.complete(
        [{"role": "user", "content": "Hello, my name is Jean Dupont"}],
    )
    # result.content == "..." (actual LLM response)
    # result.provider_used == "scaleway" (EU, because PII)
"""

from sovereign_gateway.gateway import SovereignGateway
from sovereign_gateway.models.schemas import (
    CompletionResult,
    Message,
    PIIEntity,
    Provider,
    RouteResult,
    RoutingDecision,
    SupportedModel,
)
from sovereign_gateway.pii.detector import PIIDetector
from sovereign_gateway.pii.masker import PIIMasker

__version__ = "0.2.0"
__all__ = [
    "SovereignGateway",
    "PIIDetector",
    "PIIMasker",
    "CompletionResult",
    "Message",
    "RouteResult",
    "RoutingDecision",
    "PIIEntity",
    "Provider",
    "SupportedModel",
]
