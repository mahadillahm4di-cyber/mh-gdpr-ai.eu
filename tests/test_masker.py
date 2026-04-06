"""Tests for PII masking — ensures PII is replaced with safe placeholders."""

from __future__ import annotations

import pytest

from sovereign_gateway import PIIMasker


class TestEmailMasking:
    @pytest.mark.parametrize(
        "text,expected",
        [
            (
                "Contact me at john@example.com for details.",
                "Contact me at [EMAIL_REDACTED] for details.",
            ),
            (
                "Emails: alice@company.org and bob@domain.co.uk",
                "Emails: [EMAIL_REDACTED] and [EMAIL_REDACTED]",
            ),
        ],
        ids=["single", "multiple"],
    )
    def test_masks_emails(self, masker: PIIMasker, text: str, expected: str) -> None:
        masked, types = masker.mask(text)
        assert masked == expected
        assert "EMAIL_ADDRESS" in types


class TestPhoneMasking:
    def test_masks_french_phone(self, masker: PIIMasker) -> None:
        masked, types = masker.mask("Call +33 6 12 34 56 78 please")
        assert "PHONE_NUMBER" in types
        assert "[PHONE_REDACTED]" in masked
        assert "33 6 12" not in masked


class TestCreditCardMasking:
    def test_masks_card_numbers(self, masker: PIIMasker) -> None:
        masked, types = masker.mask("Card: 4111 1111 1111 1111")
        assert "CREDIT_CARD" in types
        assert "[CARD_REDACTED]" in masked
        assert "4111" not in masked


class TestIBANMasking:
    def test_masks_iban(self, masker: PIIMasker) -> None:
        masked, types = masker.mask("IBAN: FR76 3000 6000 0112 3456 7890 189")
        assert "IBAN_CODE" in types
        assert "[IBAN_REDACTED]" in masked
        assert "FR76" not in masked


class TestSSNMasking:
    def test_masks_us_ssn(self, masker: PIIMasker) -> None:
        masked, types = masker.mask("SSN: 123-45-6789")
        assert "US_SSN" in types
        assert "[SSN_REDACTED]" in masked
        assert "123-45" not in masked

    def test_masks_french_nir(self, masker: PIIMasker) -> None:
        masked, types = masker.mask("NIR: 1 85 05 78 006 084 36")
        assert "FR_NIR" in types
        assert "[NIR_REDACTED]" in masked


class TestMessageMasking:
    def test_masks_across_messages(self, masker: PIIMasker) -> None:
        messages = [
            {"role": "user", "content": "My email is test@example.com"},
            {"role": "assistant", "content": "Got it."},
            {"role": "user", "content": "Card: 4111 1111 1111 1111"},
        ]
        masked_msgs, types = masker.mask_messages(messages)
        assert len(masked_msgs) == 3
        assert "EMAIL_ADDRESS" in types
        assert "CREDIT_CARD" in types
        assert "test@example.com" not in masked_msgs[0]["content"]
        assert "4111" not in masked_msgs[2]["content"]


class TestCleanText:
    def test_no_masking_on_clean_text(self, masker: PIIMasker) -> None:
        text = "The weather is nice today"
        masked, types = masker.mask(text)
        assert masked == text
        assert types == []
