"""SovereignGateway — main entry point for the GDPR-compliant AI gateway.

This is the primary class users interact with. It wraps PII detection
and sovereign routing into a single, simple interface.

Example:
    from sovereign_gateway import SovereignGateway

    gateway = SovereignGateway()

    # Analyze a prompt for PII and get routing decision
    result = gateway.route(
        messages=[{"role": "user", "content": "My email is jean@company.fr"}],
    )
    print(result.forced_eu_routing)  # True
    print(result.pii_types)          # ["EMAIL_ADDRESS"]
    print(result.gdpr_compliant)     # True
"""

from __future__ import annotations

import structlog

from sovereign_gateway.models.schemas import (
    Message,
    RouteResult,
    SupportedModel,
)
from sovereign_gateway.pii.detector import PIIDetector
from sovereign_gateway.pii.masker import PIIMasker
from sovereign_gateway.router.sovereign import SovereignRouter

logger = structlog.get_logger(__name__)


class SovereignGateway:
    """GDPR-compliant AI gateway with automatic PII detection and EU routing.

    The gateway analyzes every prompt for personal data (PII) using
    dual-layer detection (Presidio NLP + regex). When PII is found,
    the request is forcibly routed to EU-based providers. When no PII
    is present, the cheapest available provider is used.

    Features:
        - Real-time PII detection in <50ms
        - 15+ entity types (email, phone, IBAN, SSN, names, etc.)
        - Automatic EU routing when PII detected
        - Compliance-ready audit logs (types only, never PII content)
        - Regex fallback guarantees detection even without Presidio

    Example:
        gateway = SovereignGateway()

        # Simple check
        result = gateway.route([
            {"role": "user", "content": "Analyze this data for John Smith"}
        ])

        if result.pii_detected:
            print(f"PII found: {result.pii_types}")
            print(f"Routed to EU: {result.forced_eu_routing}")

        # Mask PII before logging
        masked = gateway.mask("Email: jean@example.fr")
        print(masked)  # "Email: [EMAIL_REDACTED]"
    """

    def __init__(
        self,
        pii_score_threshold: float = 0.5,
        use_presidio: bool = True,
    ) -> None:
        """Initialize the gateway.

        Args:
            pii_score_threshold: Minimum confidence for PII detection (0.0-1.0).
            use_presidio: Enable Presidio NLP detection. Falls back to regex if False
                or if Presidio is not installed.
        """
        self._detector = PIIDetector(
            score_threshold=pii_score_threshold,
            use_presidio=use_presidio,
        )
        self._masker = PIIMasker()
        self._router = SovereignRouter(pii_detector=self._detector)
        self._log = logger.bind(component="sovereign_gateway")

    def route(
        self,
        messages: list[dict[str, str]] | list[Message],
        model: str | SupportedModel | None = None,
        request_id: str = "",
    ) -> RouteResult:
        """Analyze messages for PII and return a routing decision.

        This is the main method. Pass your chat messages and get back
        a complete routing decision with GDPR compliance metadata.

        Args:
            messages: Chat messages as dicts or Message objects.
            model: Optional model preference (e.g., "mistral-7b").
            request_id: Optional trace ID for logging.

        Returns:
            RouteResult with routing decision, PII detection results,
            and compliance flags.
        """
        # Normalize messages to Message objects
        normalized: list[Message] = []
        for msg in messages:
            if isinstance(msg, Message):
                normalized.append(msg)
            else:
                normalized.append(Message(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                ))

        # Normalize model
        model_hint: SupportedModel | None = None
        if model is not None:
            if isinstance(model, SupportedModel):
                model_hint = model
            else:
                try:
                    model_hint = SupportedModel(model)
                except ValueError:
                    self._log.warning("unknown_model", model=model)

        return self._router.analyze_and_route(
            messages=normalized,
            model_hint=model_hint,
            request_id=request_id,
        )

    def detect_pii(self, text: str) -> list[str]:
        """Detect PII types in text.

        Args:
            text: Text to scan for PII.

        Returns:
            List of PII type names found (e.g., ["EMAIL_ADDRESS", "PERSON"]).
        """
        return self._detector.detect_types(text)

    def has_pii(self, text: str) -> bool:
        """Quick check: does the text contain any PII?

        Args:
            text: Text to scan.

        Returns:
            True if any PII is detected.
        """
        return self._detector.has_pii(text)

    def mask(self, text: str) -> str:
        """Mask all PII in text with safe placeholders.

        Args:
            text: Text containing potential PII.

        Returns:
            Text with all PII replaced by type-specific placeholders.
        """
        masked, _ = self._masker.mask(text)
        return masked

    def mask_messages(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Mask PII in all chat messages.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.

        Returns:
            Messages with PII masked in content fields.
        """
        masked, _ = self._masker.mask_messages(messages)
        return masked
