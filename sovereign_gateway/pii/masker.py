"""PII masking — replaces detected PII with safe placeholders.

Masking is deterministic per-type but not reversible,
ensuring zero-knowledge of prompt content in logs.

Example:
    masker = PIIMasker()
    masked, types = masker.mask("Email me at jean@company.fr")
    # masked = "Email me at [EMAIL_REDACTED]"
    # types = ["EMAIL_ADDRESS"]
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Detection patterns (same as detector.py for standalone use)
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

_PATTERN_ORDER: list[str] = [
    "EMAIL_ADDRESS", "IBAN_CODE", "CREDIT_CARD", "US_SSN",
    "FR_NIR", "IP_ADDRESS", "PHONE_NUMBER",
]

_MASKS: dict[str, str] = {
    "EMAIL_ADDRESS": "[EMAIL_REDACTED]",
    "PHONE_NUMBER": "[PHONE_REDACTED]",
    "CREDIT_CARD": "[CARD_REDACTED]",
    "US_SSN": "[SSN_REDACTED]",
    "FR_NIR": "[NIR_REDACTED]",
    "IP_ADDRESS": "[IP_REDACTED]",
    "IBAN_CODE": "[IBAN_REDACTED]",
}


class PIIMasker:
    """Detects and masks PII in text content.

    Thread-safe: no mutable state. All patterns are compiled at import time.

    Example:
        masker = PIIMasker()
        masked, types = masker.mask("Call +33 6 12 34 56 78")
        # masked = "Call [PHONE_REDACTED]"
        # types = ["PHONE_NUMBER"]
    """

    def __init__(self, log_detections: bool = True) -> None:
        self._log_detections = log_detections
        self._log = logger.bind(component="pii_masker")

    def detect(self, text: str) -> list[str]:
        """Detect PII types present in text without masking.

        Args:
            text: Input text to scan.

        Returns:
            List of PII type names found.
        """
        found: list[str] = []
        for pii_type in _PATTERN_ORDER:
            pattern = _PII_PATTERNS.get(pii_type)
            if pattern and pattern.search(text):
                found.append(pii_type)
        return found

    def mask(self, text: str) -> tuple[str, list[str]]:
        """Detect and mask all PII in text.

        Args:
            text: Input text that may contain PII.

        Returns:
            Tuple of (masked_text, pii_types_found).
        """
        found: list[str] = []
        result = text

        for pii_type in _PATTERN_ORDER:
            pattern = _PII_PATTERNS.get(pii_type)
            mask_str = _MASKS.get(pii_type, "[PII_REDACTED]")
            if pattern is None:
                continue

            if pattern.search(result):
                found.append(pii_type)
                result = pattern.sub(mask_str, result)

        if found and self._log_detections:
            self._log.info(
                "pii_masked",
                pii_types=found,
                count=len(found),
            )

        return result, found

    def mask_messages(
        self,
        messages: list[dict[str, str]],
    ) -> tuple[list[dict[str, str]], list[str]]:
        """Mask PII across all chat messages.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.

        Returns:
            Tuple of (masked_messages, all_pii_types_found).
        """
        all_types: list[str] = []
        masked: list[dict[str, str]] = []

        for msg in messages:
            content = msg.get("content", "")
            masked_content, types = self.mask(content)
            all_types.extend(types)
            masked.append({
                "role": msg.get("role", "user"),
                "content": masked_content,
            })

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_types: list[str] = []
        for t in all_types:
            if t not in seen:
                seen.add(t)
                unique_types.append(t)

        return masked, unique_types
