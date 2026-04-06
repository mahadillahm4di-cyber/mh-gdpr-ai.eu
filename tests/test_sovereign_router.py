"""Tests for sovereign routing — GDPR-compliant EU routing when PII detected."""

from __future__ import annotations

import pytest

from sovereign_gateway import SovereignGateway
from sovereign_gateway.models.schemas import Message, RoutingDecision


class TestEURoutingOnPII:
    """When PII is detected, routing MUST be forced to EU providers."""

    @pytest.mark.parametrize(
        "content,expected_pii_type",
        [
            ("My email is jean@company.fr", "EMAIL_ADDRESS"),
            ("IBAN: FR76 3000 6000 0112 3456 7890 189", "IBAN_CODE"),
            ("Card: 4111 1111 1111 1111", "CREDIT_CARD"),
            ("SSN: 123-45-6789", "US_SSN"),
        ],
        ids=["email", "iban", "credit_card", "ssn"],
    )
    def test_forces_eu_when_pii_detected(
        self,
        gateway: SovereignGateway,
        content: str,
        expected_pii_type: str,
    ) -> None:
        result = gateway.route([{"role": "user", "content": content}])

        assert result.pii_detected is True
        assert result.forced_eu_routing is True
        assert result.gdpr_compliant is True
        assert result.decision == RoutingDecision.EU_ONLY
        assert expected_pii_type in result.pii_types


class TestCheapestRoutingNoPII:
    """When no PII is detected, route to cheapest provider."""

    @pytest.mark.parametrize(
        "content",
        [
            "Summarize this article about quantum computing.",
            "Write a Python function to sort a list.",
            "What is the capital of France?",
            "Explain the theory of relativity.",
        ],
        ids=["summarize", "code", "geography", "science"],
    )
    def test_cheapest_when_no_pii(
        self,
        gateway: SovereignGateway,
        content: str,
    ) -> None:
        result = gateway.route([{"role": "user", "content": content}])

        assert result.pii_detected is False
        assert result.forced_eu_routing is False
        assert result.decision == RoutingDecision.CHEAPEST


class TestComplianceSummary:
    """Verify the compliance summary output for audit logs."""

    def test_compliance_summary_with_pii(self, gateway: SovereignGateway) -> None:
        result = gateway.route([
            {"role": "user", "content": "My email is test@example.com"},
        ])
        summary = result.compliance_summary

        assert summary["gdpr_compliant"] is True
        assert summary["pii_detected"] is True
        assert "EMAIL_ADDRESS" in summary["pii_types"]
        assert summary["provider_region"] == "EU"

    def test_compliance_summary_without_pii(self, gateway: SovereignGateway) -> None:
        result = gateway.route([
            {"role": "user", "content": "Hello, how are you?"},
        ])
        summary = result.compliance_summary

        assert summary["pii_detected"] is False
        assert summary["provider_region"] == "ANY"


class TestMultiplePIITypes:
    """Verify detection of multiple PII types in a single message."""

    def test_detects_email_and_phone(self, gateway: SovereignGateway) -> None:
        result = gateway.route([{
            "role": "user",
            "content": "Contact jean@company.fr or call +33 6 12 34 56 78",
        }])

        assert result.pii_detected is True
        assert result.forced_eu_routing is True
        assert "EMAIL_ADDRESS" in result.pii_types
        assert "PHONE_NUMBER" in result.pii_types

    def test_detects_iban_and_email(self, gateway: SovereignGateway) -> None:
        result = gateway.route([{
            "role": "user",
            "content": "Send to jean@bank.fr, IBAN: FR76 3000 6000 0112 3456 7890 189",
        }])

        assert result.pii_detected is True
        assert "EMAIL_ADDRESS" in result.pii_types
        assert "IBAN_CODE" in result.pii_types


class TestMessageNormalization:
    """Verify the gateway accepts both dicts and Message objects."""

    def test_accepts_dicts(self, gateway: SovereignGateway) -> None:
        result = gateway.route([{"role": "user", "content": "Hello"}])
        assert result is not None

    def test_accepts_message_objects(self, gateway: SovereignGateway) -> None:
        result = gateway.route([Message(role="user", content="Hello")])
        assert result is not None

    def test_only_scans_user_messages(self, gateway: SovereignGateway) -> None:
        """System/assistant messages should not trigger PII routing."""
        result = gateway.route([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "The answer is 4."},
        ])
        assert result.pii_detected is False
