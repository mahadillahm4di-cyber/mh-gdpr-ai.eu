"""Tests for PII detection — emails, phones, IBANs, credit cards, SSNs."""

from __future__ import annotations

import pytest

from sovereign_gateway import PIIDetector


class TestEmailDetection:
    """Verify email address detection."""

    @pytest.mark.parametrize(
        "text",
        [
            "Contact me at john@example.com for details.",
            "Emails: alice@company.org and bob.smith+tag@sub.domain.co.uk",
            "user_name.123@long-domain-name.info",
        ],
        ids=["simple", "multiple", "complex"],
    )
    def test_detects_emails(self, detector: PIIDetector, text: str) -> None:
        types = detector.detect_types(text)
        assert "EMAIL_ADDRESS" in types

    def test_no_false_positive_on_plain_text(self, detector: PIIDetector) -> None:
        types = detector.detect_types("Hello, how are you today?")
        assert "EMAIL_ADDRESS" not in types


class TestPhoneDetection:
    """Verify international phone number detection."""

    @pytest.mark.parametrize(
        "text",
        [
            "Call me at +33 6 12 34 56 78.",
            "My number is +1 (555) 123-4567.",
            "Phone: 06 12 34 56 78",
            "Reach me at +44 20 7946 0958.",
        ],
        ids=["french_intl", "us_format", "french_local", "uk_format"],
    )
    def test_detects_phones(self, detector: PIIDetector, text: str) -> None:
        types = detector.detect_types(text)
        assert "PHONE_NUMBER" in types


class TestCreditCardDetection:
    """Verify credit card number detection."""

    @pytest.mark.parametrize(
        "text",
        [
            "Card: 4111 1111 1111 1111",
            "CC: 4111-1111-1111-1111",
            "Pay with 5500 0000 0000 0004 please.",
        ],
        ids=["spaces", "dashes", "embedded"],
    )
    def test_detects_credit_cards(self, detector: PIIDetector, text: str) -> None:
        types = detector.detect_types(text)
        assert "CREDIT_CARD" in types


class TestIBANDetection:
    """Verify IBAN detection."""

    @pytest.mark.parametrize(
        "text",
        [
            "IBAN: FR76 3000 6000 0112 3456 7890 189",
            "Transfer to DE89 3704 0044 0532 0130 00",
            "Account GB29 NWBK 6016 1331 9268 19",
        ],
        ids=["french", "german", "british"],
    )
    def test_detects_ibans(self, detector: PIIDetector, text: str) -> None:
        types = detector.detect_types(text)
        assert "IBAN_CODE" in types


class TestSSNDetection:
    """Verify social security number detection."""

    def test_detects_us_ssn(self, detector: PIIDetector) -> None:
        types = detector.detect_types("SSN: 123-45-6789")
        assert "US_SSN" in types

    def test_detects_french_nir(self, detector: PIIDetector) -> None:
        types = detector.detect_types("NIR: 1 85 05 78 006 084 36")
        assert "FR_NIR" in types


class TestIPDetection:
    """Verify IPv4 address detection."""

    @pytest.mark.parametrize(
        "text",
        [
            "Server at 192.168.1.1",
            "Access from 10.0.0.255",
            "IP: 172.16.0.1",
        ],
        ids=["private_c", "private_a", "private_b"],
    )
    def test_detects_ips(self, detector: PIIDetector, text: str) -> None:
        types = detector.detect_types(text)
        assert "IP_ADDRESS" in types


class TestNoPII:
    """Verify no false positives on clean text."""

    @pytest.mark.parametrize(
        "text",
        [
            "The weather is nice today.",
            "Please summarize this article about machine learning.",
            "What is the capital of France?",
            "Write a Python function to sort a list.",
            "Explain quantum computing in simple terms.",
        ],
        ids=["weather", "summarize", "geography", "code", "science"],
    )
    def test_no_pii_detected(self, detector: PIIDetector, text: str) -> None:
        types = detector.detect_types(text)
        # Should not detect email, credit card, SSN, IBAN on clean text
        assert "EMAIL_ADDRESS" not in types
        assert "CREDIT_CARD" not in types
        assert "US_SSN" not in types
        assert "IBAN_CODE" not in types


class TestHasPII:
    """Test the fast has_pii() method."""

    def test_returns_true_when_pii_present(self, detector: PIIDetector) -> None:
        assert detector.has_pii("Email: test@example.com") is True

    def test_returns_false_when_clean(self, detector: PIIDetector) -> None:
        assert detector.has_pii("Hello world") is False
