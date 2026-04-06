"""mh-gdpr-ai.eu — GDPR-compliant LLM routing with real-time PII detection.

Automatically detects personal data in LLM prompts and forces EU-only routing
when PII is found. No PII = cheapest provider. Full compliance, zero overhead.

Usage:
    from sovereign_gateway import SovereignGateway

    gateway = SovereignGateway()
    result = await gateway.route(
        messages=[{"role": "user", "content": "Hello, my name is Jean Dupont"}],
    )
    # result.forced_eu_routing == True (PII detected: PERSON)
"""

from sovereign_gateway.gateway import SovereignGateway
from sovereign_gateway.pii.detector import PIIDetector
from sovereign_gateway.pii.masker import PIIMasker
from sovereign_gateway.models.schemas import (
    Message,
    RouteResult,
    RoutingDecision,
    PIIEntity,
    Provider,
    SupportedModel,
)

__version__ = "0.1.0"
__all__ = [
    "SovereignGateway",
    "PIIDetector",
    "PIIMasker",
    "Message",
    "RouteResult",
    "RoutingDecision",
    "PIIEntity",
    "Provider",
    "SupportedModel",
]
