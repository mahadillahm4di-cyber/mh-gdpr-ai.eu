"""Tests for SovereignGateway.complete() — end-to-end LLM routing."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sovereign_gateway import SovereignGateway


@pytest.fixture
def mock_provider_response():
    """Standard OpenAI-compatible API response."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
        },
    }


@pytest.fixture
def gateway_with_providers():
    """Gateway with mock EU + non-EU providers configured."""
    return SovereignGateway(
        use_presidio=False,
        providers={
            "scaleway": {"api_key": "scw-test-key"},
            "together_ai": {"api_key": "tok-test-key"},
        },
    )


class TestCompleteEndToEnd:
    """Test the complete() method — PII detection + routing + LLM call."""

    def test_pii_routes_to_eu_provider(
        self, gateway_with_providers, mock_provider_response
    ):
        with patch.object(
            gateway_with_providers._client, "call", return_value=mock_provider_response
        ) as mock_call:
            result = gateway_with_providers.complete(
                [{"role": "user", "content": "Email jean@bnp.fr about his account"}]
            )

        assert result.pii_detected is True
        assert result.forced_eu_routing is True
        assert result.gdpr_compliant is True
        assert result.provider_used == "scaleway"
        assert result.content == "Hello! How can I help you today?"
        assert result.tokens_used == 20
        assert "EMAIL_ADDRESS" in result.pii_types

        # Verify call was made to scaleway (EU provider)
        call_args = mock_call.call_args
        assert call_args.kwargs["config"].name == "scaleway"
        assert call_args.kwargs["config"].is_eu is True

    def test_no_pii_routes_to_cheapest(
        self, gateway_with_providers, mock_provider_response
    ):
        with patch.object(
            gateway_with_providers._client, "call", return_value=mock_provider_response
        ) as mock_call:
            result = gateway_with_providers.complete(
                [{"role": "user", "content": "Summarize this quarterly report"}]
            )

        assert result.pii_detected is False
        assert result.forced_eu_routing is False
        assert result.content == "Hello! How can I help you today?"
        mock_call.assert_called_once()

    def test_compliance_summary_available(
        self, gateway_with_providers, mock_provider_response
    ):
        with patch.object(
            gateway_with_providers._client, "call", return_value=mock_provider_response
        ):
            result = gateway_with_providers.complete(
                [{"role": "user", "content": "Contact jean@company.fr"}]
            )

        summary = result.compliance_summary
        assert summary["gdpr_compliant"] is True
        assert summary["pii_detected"] is True
        assert "EMAIL_ADDRESS" in summary["pii_types"]
        assert summary["routing_decision"] == "eu_only"
        assert summary["provider_region"] == "EU"

    def test_latency_tracked(
        self, gateway_with_providers, mock_provider_response
    ):
        with patch.object(
            gateway_with_providers._client, "call", return_value=mock_provider_response
        ):
            result = gateway_with_providers.complete(
                [{"role": "user", "content": "Hello world"}]
            )

        assert result.latency_ms > 0


class TestCompleteErrors:
    """Test error cases for complete()."""

    def test_no_providers_raises(self):
        gateway = SovereignGateway(use_presidio=False)
        with pytest.raises(RuntimeError, match="No providers configured"):
            gateway.complete([{"role": "user", "content": "Hello"}])

    def test_pii_but_no_eu_provider_raises(self):
        gateway = SovereignGateway(
            use_presidio=False,
            providers={"together_ai": {"api_key": "tok-xxx"}},
        )
        with pytest.raises(RuntimeError, match="no EU provider configured"):
            gateway.complete(
                [{"role": "user", "content": "Email jean@bnp.fr"}]
            )


class TestProviderSelection:
    """Test provider selection logic."""

    def test_eu_provider_selected_for_pii(self):
        gateway = SovereignGateway(
            use_presidio=False,
            providers={
                "scaleway": {"api_key": "scw-key"},
                "together_ai": {"api_key": "tok-key"},
            },
        )
        provider = gateway._select_provider("scaleway", eu_only=True)
        assert provider.name == "scaleway"
        assert provider.is_eu is True

    def test_cheapest_provider_for_no_pii(self):
        gateway = SovereignGateway(
            use_presidio=False,
            providers={
                "scaleway": {"api_key": "scw-key"},
                "together_ai": {"api_key": "tok-key"},
            },
        )
        provider = gateway._select_provider("scaleway", eu_only=False)
        assert provider.name == "scaleway"  # Priority 1

    def test_fallback_to_next_eu_provider(self):
        gateway = SovereignGateway(
            use_presidio=False,
            providers={
                "ovhcloud": {"api_key": "ovh-key"},
                "together_ai": {"api_key": "tok-key"},
            },
        )
        provider = gateway._select_provider("scaleway", eu_only=True)
        assert provider.name == "ovhcloud"
        assert provider.is_eu is True

    def test_providers_property(self):
        gateway = SovereignGateway(
            use_presidio=False,
            providers={"scaleway": {"api_key": "scw-key"}},
        )
        providers = gateway.providers
        assert "scaleway" in providers
        assert providers["scaleway"].api_key == "scw-key"


class TestProviderConfig:
    """Test provider configuration parsing."""

    def test_parse_with_custom_base_url(self):
        gateway = SovereignGateway(
            use_presidio=False,
            providers={
                "scaleway": {
                    "api_key": "scw-key",
                    "base_url": "https://custom.api.eu/v1",
                },
            },
        )
        assert gateway.providers["scaleway"].base_url == "https://custom.api.eu/v1"

    def test_parse_with_default_base_url(self):
        gateway = SovereignGateway(
            use_presidio=False,
            providers={"scaleway": {"api_key": "scw-key"}},
        )
        assert "scaleway" in gateway.providers["scaleway"].base_url

    def test_empty_api_key_skipped(self):
        gateway = SovereignGateway(
            use_presidio=False,
            providers={"scaleway": {"api_key": ""}},
        )
        assert len(gateway.providers) == 0
