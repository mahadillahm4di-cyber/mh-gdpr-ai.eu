"""Shared test fixtures for mh-gdpr-ai.eu."""

from __future__ import annotations

import pytest

from sovereign_gateway import PIIDetector, PIIMasker, SovereignGateway


@pytest.fixture
def detector() -> PIIDetector:
    """PII detector with Presidio disabled (regex-only for fast tests)."""
    return PIIDetector(use_presidio=False)


@pytest.fixture
def masker() -> PIIMasker:
    return PIIMasker(log_detections=False)


@pytest.fixture
def gateway() -> SovereignGateway:
    """Gateway with regex-only PII detection for fast tests."""
    return SovereignGateway(use_presidio=False)
