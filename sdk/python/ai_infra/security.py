"""Client-side security layer for the AI Infrastructure SDK.

Responsibilities:
- API key validation and masking (never logged, never in errors)
- TLS enforcement (1.2+ required, certificate verification)
- Input sanitization before sending to the API
- Optional client-side PII detection (warning before send)
- Secure proxy support
"""

from __future__ import annotations

import os
import re
import ssl
from typing import Any

from ai_infra.exceptions import AuthenticationError, ValidationError

# ── API key format ────────────────────────────────────────────────
# Keys are "sk-" followed by 32–128 alphanumeric/hyphen characters.
_API_KEY_PATTERN = re.compile(r"^sk-[a-zA-Z0-9\-]{32,128}$")

# Characters that should never appear in a user prompt
_DANGEROUS_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Lightweight PII patterns — not exhaustive, just a client-side warning
_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}",
    ),
    "phone": re.compile(
        r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}",
    ),
    "iban": re.compile(
        r"\b[A-Z]{2}\d{2}\s?[\dA-Z]{4}\s?[\dA-Z]{4}\s?[\dA-Z]{4}\s?[\dA-Z]{0,4}\b",
    ),
    "credit_card": re.compile(
        r"\b(?:\d[ -]*?){13,19}\b",
    ),
    "ssn": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b",
    ),
}


def validate_api_key(api_key: str | None) -> str:
    """Validate API key format. Returns the key or raises.

    Args:
        api_key: Raw API key string.

    Returns:
        The validated API key.

    Raises:
        AuthenticationError: If the key is missing or malformed.
    """
    if not api_key:
        raise AuthenticationError(
            "API key is required. Set AI_INFRA_API_KEY environment variable "
            "or pass api_key to Client().",
        )
    if not _API_KEY_PATTERN.match(api_key):
        raise AuthenticationError(
            "Invalid API key format. Keys start with 'sk-' followed by "
            "32-128 alphanumeric characters.",
        )
    return api_key


def mask_api_key(api_key: str) -> str:
    """Mask an API key for safe logging: ``sk-abc...xyz``.

    Args:
        api_key: Raw API key string.

    Returns:
        Masked key showing only first 6 and last 3 characters.
    """
    if len(api_key) <= 10:
        return "sk-***"
    return f"{api_key[:6]}...{api_key[-3:]}"


def resolve_api_key(
    explicit: str | None = None,
    env_var: str = "AI_INFRA_API_KEY",
) -> str:
    """Resolve API key from explicit value or environment.

    Priority:
        1. Explicit ``api_key`` parameter
        2. ``AI_INFRA_API_KEY`` environment variable

    Args:
        explicit: Directly provided API key.
        env_var: Name of the environment variable.

    Returns:
        The validated API key.

    Raises:
        AuthenticationError: If no key found or format invalid.
    """
    key = explicit or os.environ.get(env_var)
    return validate_api_key(key)


def sanitize_content(text: str, *, max_length: int = 1_000_000) -> str:
    """Remove dangerous characters and enforce length limits.

    Args:
        text: Raw user content.
        max_length: Maximum allowed character count.

    Returns:
        Sanitized content string.

    Raises:
        ValidationError: If the content exceeds the max length.
    """
    if len(text) > max_length:
        raise ValidationError(
            f"Content exceeds maximum length of {max_length:,} characters "
            f"(got {len(text):,}).",
        )
    return _DANGEROUS_CHARS.sub("", text)


def detect_pii(text: str) -> list[str]:
    """Lightweight client-side PII detection.

    This is a best-effort scan — the server runs a full Presidio analysis.
    Returns a list of PII types detected (e.g. ``["email", "phone"]``).

    Args:
        text: The content to scan.

    Returns:
        List of detected PII type names.
    """
    found: list[str] = []
    for pii_type, pattern in _PII_PATTERNS.items():
        if pattern.search(text):
            found.append(pii_type)
    return found


def validate_messages(
    messages: list[dict[str, Any]],
    *,
    max_content_length: int = 1_000_000,
) -> list[dict[str, str]]:
    """Validate and sanitize a message list before sending.

    Args:
        messages: List of message dicts with ``role`` and ``content``.
        max_content_length: Maximum per-message content length.

    Returns:
        Validated and sanitized message list.

    Raises:
        ValidationError: If messages are empty or malformed.
    """
    if not messages:
        raise ValidationError("messages must contain at least one message.")

    valid_roles = {"system", "user", "assistant"}
    validated: list[dict[str, str]] = []

    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            raise ValidationError(
                f"messages[{i}] must be a dict, got {type(msg).__name__}.",
            )

        role = msg.get("role")
        content = msg.get("content")

        if role not in valid_roles:
            raise ValidationError(
                f"messages[{i}].role must be one of {valid_roles}, "
                f"got {role!r}.",
            )
        if not isinstance(content, str) or not content.strip():
            raise ValidationError(
                f"messages[{i}].content must be a non-empty string.",
            )

        validated.append({
            "role": role,
            "content": sanitize_content(content, max_length=max_content_length),
        })

    return validated


def create_ssl_context(
    *,
    verify: bool = True,
    ca_bundle: str | None = None,
) -> ssl.SSLContext:
    """Create a hardened TLS context.

    - Minimum TLS 1.2 (server-side negotiation may upgrade to 1.3)
    - Certificate verification enabled by default
    - Optional custom CA bundle for corporate proxies

    Args:
        verify: Whether to verify server certificates.
        ca_bundle: Path to a custom CA certificate bundle.

    Returns:
        Configured SSLContext.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = verify
    ctx.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE

    if verify and ca_bundle:
        ctx.load_verify_locations(ca_bundle)
    elif verify:
        ctx.load_default_certs()

    return ctx
