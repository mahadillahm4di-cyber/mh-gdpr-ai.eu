"""Tests for the security module."""

from __future__ import annotations

import os
import ssl
from unittest.mock import patch

import pytest

from ai_infra.exceptions import AuthenticationError, ValidationError
from ai_infra.security import (
    create_ssl_context,
    detect_pii,
    mask_api_key,
    resolve_api_key,
    sanitize_content,
    validate_api_key,
    validate_messages,
)


class TestValidateApiKey:
    def test_valid_key(self) -> None:
        key = "sk-" + "a" * 32
        assert validate_api_key(key) == key

    def test_valid_key_long(self) -> None:
        key = "sk-" + "a1b2c3d4" * 16  # 128 chars
        assert validate_api_key(key) == key

    def test_none_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="required"):
            validate_api_key(None)

    def test_empty_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="required"):
            validate_api_key("")

    def test_no_prefix_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="format"):
            validate_api_key("abc" + "x" * 32)

    def test_too_short_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="format"):
            validate_api_key("sk-short")

    def test_invalid_chars_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="format"):
            validate_api_key("sk-" + "a" * 31 + "!")


class TestMaskApiKey:
    def test_masks_middle(self) -> None:
        key = "sk-abcdefghijklmnop1234567890abcdef"
        masked = mask_api_key(key)
        assert masked.startswith("sk-abc")
        assert masked.endswith("def")
        assert "..." in masked
        assert key not in masked

    def test_short_key_fully_masked(self) -> None:
        masked = mask_api_key("sk-short")
        assert masked == "sk-***"


class TestResolveApiKey:
    def test_explicit_takes_priority(self) -> None:
        key = "sk-" + "a" * 32
        result = resolve_api_key(explicit=key)
        assert result == key

    def test_env_var_fallback(self) -> None:
        key = "sk-" + "b" * 32
        with patch.dict(os.environ, {"AI_INFRA_API_KEY": key}):
            result = resolve_api_key()
            assert result == key

    def test_custom_env_var(self) -> None:
        key = "sk-" + "c" * 32
        with patch.dict(os.environ, {"MY_KEY": key}):
            result = resolve_api_key(env_var="MY_KEY")
            assert result == key

    def test_no_key_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("AI_INFRA_API_KEY", None)
            with pytest.raises(AuthenticationError):
                resolve_api_key()


class TestSanitizeContent:
    def test_normal_content_passes(self) -> None:
        assert sanitize_content("Hello world") == "Hello world"

    def test_removes_null_bytes(self) -> None:
        assert sanitize_content("Hello\x00world") == "Helloworld"

    def test_removes_control_chars(self) -> None:
        result = sanitize_content("Hello\x01\x02\x03world")
        assert result == "Helloworld"

    def test_preserves_newlines_and_tabs(self) -> None:
        text = "Line 1\nLine 2\tTabbed"
        assert sanitize_content(text) == text

    def test_max_length_enforced(self) -> None:
        with pytest.raises(ValidationError, match="maximum length"):
            sanitize_content("x" * 101, max_length=100)

    def test_unicode_preserved(self) -> None:
        assert sanitize_content("Bonjour le monde") == "Bonjour le monde"


class TestDetectPii:
    def test_detects_email(self) -> None:
        result = detect_pii("Contact jean@example.com for info")
        assert "email" in result

    def test_detects_phone(self) -> None:
        result = detect_pii("Call me at +33 612345678")
        assert "phone" in result

    def test_detects_iban(self) -> None:
        result = detect_pii("IBAN: FR76 1234 5678 9012 3456 7890 123")
        assert "iban" in result

    def test_detects_ssn(self) -> None:
        result = detect_pii("SSN: 123-45-6789")
        assert "ssn" in result

    def test_no_pii(self) -> None:
        result = detect_pii("The weather is nice today")
        assert result == []

    def test_multiple_pii_types(self) -> None:
        text = "Email: test@test.com, SSN: 123-45-6789"
        result = detect_pii(text)
        assert "email" in result
        assert "ssn" in result


class TestValidateMessages:
    def test_valid_messages(self) -> None:
        msgs = [{"role": "user", "content": "Hello"}]
        result = validate_messages(msgs)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_multi_turn(self) -> None:
        msgs = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "Thanks"},
        ]
        result = validate_messages(msgs)
        assert len(result) == 4

    def test_empty_raises(self) -> None:
        with pytest.raises(ValidationError, match="at least one"):
            validate_messages([])

    def test_invalid_role_raises(self) -> None:
        with pytest.raises(ValidationError, match="role"):
            validate_messages([{"role": "admin", "content": "Hi"}])

    def test_missing_content_raises(self) -> None:
        with pytest.raises(ValidationError, match="content"):
            validate_messages([{"role": "user"}])

    def test_empty_content_raises(self) -> None:
        with pytest.raises(ValidationError, match="content"):
            validate_messages([{"role": "user", "content": ""}])

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValidationError, match="content"):
            validate_messages([{"role": "user", "content": "   "}])

    def test_non_dict_raises(self) -> None:
        with pytest.raises(ValidationError, match="dict"):
            validate_messages(["not a dict"])

    def test_sanitizes_control_chars(self) -> None:
        msgs = [{"role": "user", "content": "Hello\x00"}]
        result = validate_messages(msgs)
        assert result[0]["content"] == "Hello"


class TestCreateSslContext:
    def test_default_context(self) -> None:
        ctx = create_ssl_context()
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2
        assert ctx.check_hostname is True
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_no_verify(self) -> None:
        ctx = create_ssl_context(verify=False)
        assert ctx.check_hostname is False
        assert ctx.verify_mode == ssl.CERT_NONE
