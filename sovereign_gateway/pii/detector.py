"""PII detection engine — Presidio NLP + regex defense-in-depth.

Detects personally identifiable information in text using two layers:
1. Microsoft Presidio (NLP-based, high accuracy) — primary
2. Regex patterns (deterministic, fast) — always runs as fallback

This dual-layer approach guarantees detection even if Presidio is unavailable.
Never logs actual PII content — only types and counts.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

from sovereign_gateway.models.schemas import PIIEntity

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Regex patterns — deterministic fallback layer
# ---------------------------------------------------------------------------

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "EMAIL_ADDRESS": re.compile(
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
    ),
    "PHONE_NUMBER": re.compile(
        r"(?<!\d)(?:\+\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}(?:\s?\d{2,4})?(?!\d)",
    ),
    "CREDIT_CARD": re.compile(
        r"\b(?:\d{4}[\s.-]?){3}\d{4}\b",
    ),
    "US_SSN": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b",
    ),
    "FR_NIR": re.compile(
        r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b",
    ),
    "IP_ADDRESS": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
    ),
    "IBAN_CODE": re.compile(
        r"\b[A-Z]{2}\d{2}\s?(?:[A-Z0-9]{4}\s?){3,7}[A-Z0-9]{1,4}\b",
    ),
}

# Process specific patterns before generic ones to avoid false matches
_PATTERN_ORDER: list[str] = [
    "EMAIL_ADDRESS", "IBAN_CODE", "CREDIT_CARD", "US_SSN",
    "FR_NIR", "IP_ADDRESS", "PHONE_NUMBER",
]

# Extended Presidio entity types for GDPR compliance
PRESIDIO_ENTITIES: list[str] = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "IBAN_CODE",
    "CREDIT_CARD",
    "CRYPTO",
    "IP_ADDRESS",
    "MEDICAL_LICENSE",
    "NRP",
    "LOCATION",
    "DATE_TIME",
    "US_SSN",
    "UK_NHS",
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
]


# ---------------------------------------------------------------------------
# Presidio singleton (lazy-loaded)
# ---------------------------------------------------------------------------

_presidio_analyzer = None
_presidio_available: bool | None = None


def _get_presidio_analyzer() -> Any:
    """Lazy-load the Presidio analyzer.

    Returns the analyzer instance, or None if Presidio is not installed.
    Install with: pip install presidio-analyzer presidio-anonymizer
    """
    global _presidio_analyzer, _presidio_available

    if _presidio_available is False:
        return None
    if _presidio_analyzer is not None:
        return _presidio_analyzer

    try:
        from presidio_analyzer import AnalyzerEngine

        _presidio_analyzer = AnalyzerEngine()
        _presidio_available = True
        logger.info("presidio_analyzer_initialized")
        return _presidio_analyzer
    except ImportError:
        _presidio_available = False
        logger.warning("presidio_not_installed_using_regex_only")
        return None


# ---------------------------------------------------------------------------
# PIIDetector
# ---------------------------------------------------------------------------


class PIIDetector:
    """Dual-layer PII detection: Presidio NLP + regex fallback.

    Thread-safe. All patterns are compiled at import time.

    Example:
        detector = PIIDetector()
        entities = detector.detect("Contact jean.dupont@email.fr for info")
        # [PIIEntity(entity_type="EMAIL_ADDRESS", ...)]

    Args:
        score_threshold: Minimum confidence for Presidio detections.
        use_presidio: Set False to use regex-only mode.
        language: Language for Presidio analysis.
    """

    def __init__(
        self,
        score_threshold: float = 0.5,
        use_presidio: bool = True,
        language: str = "en",
    ) -> None:
        self._score_threshold = score_threshold
        self._use_presidio = use_presidio
        self._language = language
        self._log = logger.bind(component="pii_detector")

    def detect(self, text: str) -> list[PIIEntity]:
        """Detect all PII entities in text.

        Uses Presidio as primary detector, regex as fallback.
        Both layers run for defense-in-depth.

        Args:
            text: Input text to scan for PII.

        Returns:
            List of detected PII entities with types and positions.
            Never contains the actual PII content — only metadata.
        """
        entities: list[PIIEntity] = []
        seen_spans: set[tuple[int, int]] = set()

        # Layer 1: Presidio (NLP-based)
        if self._use_presidio:
            presidio_entities = self._detect_presidio(text)
            for entity in presidio_entities:
                span = (entity.start, entity.end)
                if span not in seen_spans:
                    seen_spans.add(span)
                    entities.append(entity)

        # Layer 2: Regex (always runs — defense in depth)
        regex_entities = self._detect_regex(text)
        for entity in regex_entities:
            span = (entity.start, entity.end)
            if span not in seen_spans:
                seen_spans.add(span)
                entities.append(entity)

        if entities:
            pii_types = sorted({e.entity_type for e in entities})
            self._log.info(
                "pii_detected",
                types=pii_types,
                count=len(entities),
            )

        return entities

    def detect_types(self, text: str) -> list[str]:
        """Detect PII and return only the unique type names.

        Convenience method for routing decisions that only need
        to know which types of PII are present.

        Args:
            text: Input text to scan.

        Returns:
            Sorted list of unique PII type names found.
        """
        entities = self.detect(text)
        return sorted({e.entity_type for e in entities})

    def has_pii(self, text: str) -> bool:
        """Quick check: does the text contain any PII?

        Args:
            text: Input text to scan.

        Returns:
            True if any PII is detected.
        """
        # Fast path: check regex first (cheaper than Presidio)
        for pii_type in _PATTERN_ORDER:
            pattern = _PII_PATTERNS.get(pii_type)
            if pattern and pattern.search(text):
                return True

        # If regex found nothing, try Presidio
        if self._use_presidio:
            analyzer = _get_presidio_analyzer()
            if analyzer is not None:
                try:
                    results = analyzer.analyze(
                        text=text,
                        language=self._language,
                        entities=PRESIDIO_ENTITIES,
                        score_threshold=self._score_threshold,
                    )
                    return len(results) > 0
                except Exception:
                    pass

        return False

    def _detect_presidio(self, text: str) -> list[PIIEntity]:
        """Run Presidio NLP-based detection."""
        analyzer = _get_presidio_analyzer()
        if analyzer is None:
            return []

        try:
            results = analyzer.analyze(
                text=text,
                language=self._language,
                entities=PRESIDIO_ENTITIES,
                score_threshold=self._score_threshold,
            )
            entities = []
            for r in results:
                entities.append(PIIEntity(
                    entity_type=r.entity_type,
                    start=r.start,
                    end=r.end,
                    score=round(r.score, 3),
                    source="presidio",
                ))
                if r.score < 0.7:
                    self._log.debug(
                        "pii_low_confidence",
                        type=r.entity_type,
                        confidence=round(r.score, 3),
                    )
            return entities
        except Exception as exc:
            self._log.warning("presidio_error", error=str(exc))
            return []

    def _detect_regex(self, text: str) -> list[PIIEntity]:
        """Run regex-based PII detection."""
        entities: list[PIIEntity] = []

        for pii_type in _PATTERN_ORDER:
            pattern = _PII_PATTERNS.get(pii_type)
            if pattern is None:
                continue
            for match in pattern.finditer(text):
                entities.append(PIIEntity(
                    entity_type=pii_type,
                    start=match.start(),
                    end=match.end(),
                    score=1.0,
                    source="regex",
                ))

        return entities
