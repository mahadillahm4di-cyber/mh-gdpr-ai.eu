"""Tests for the Client class."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from ai_infra.client import Client
from ai_infra.exceptions import AuthenticationError
from ai_infra.models import RoutingMode
from ai_infra.retry import RetryConfig
from tests.conftest import TEST_API_KEY, TEST_BASE_URL


class TestClientInit:
    def test_explicit_api_key(self) -> None:
        c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL, verify_ssl=False)
        assert repr(c).startswith("Client(")
        assert "sk-tes...def" in repr(c)
        c.close()

    def test_env_api_key(self) -> None:
        with patch.dict(os.environ, {"AI_INFRA_API_KEY": TEST_API_KEY}):
            c = Client(base_url=TEST_BASE_URL, verify_ssl=False)
            c.close()

    def test_missing_key_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("AI_INFRA_API_KEY", None)
            with pytest.raises(AuthenticationError):
                Client(base_url=TEST_BASE_URL)

    def test_invalid_key_raises(self) -> None:
        with pytest.raises(AuthenticationError):
            Client(api_key="bad-key", base_url=TEST_BASE_URL)


class TestClientModes:
    def test_default_mode_none(self, client: Client) -> None:
        assert client.routing_mode is None

    def test_string_mode(self) -> None:
        c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
                    mode="best_cost", verify_ssl=False)
        assert c.routing_mode == "best_cost"
        c.close()

    def test_enum_mode(self) -> None:
        c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
                    mode=RoutingMode.EU_ONLY, verify_ssl=False)
        assert c.routing_mode == "eu_only"
        c.close()

    def test_all_mode_aliases(self) -> None:
        for mode_str in ["best_cost", "best_quality", "best_speed",
                         "balanced", "eu_only", "best_availability"]:
            c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
                       mode=mode_str, verify_ssl=False)
            assert c.routing_mode == mode_str
            c.close()


class TestClientProperties:
    def test_route_url(self, client: Client) -> None:
        assert client.route_url == f"{TEST_BASE_URL}/v1/route"

    def test_auth_headers(self, client: Client) -> None:
        headers = client.auth_headers
        assert headers["Authorization"] == f"Bearer {TEST_API_KEY}"
        assert headers["X-API-Key"] == TEST_API_KEY
        assert headers["Content-Type"] == "application/json"

    def test_timeout(self) -> None:
        c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
                    timeout=30.0, verify_ssl=False)
        assert c.timeout == 30.0
        c.close()

    def test_custom_retry_config(self) -> None:
        cfg = RetryConfig(max_retries=5)
        c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
                    retry_config=cfg, verify_ssl=False)
        assert c.retry_config.max_retries == 5
        c.close()

    def test_max_retries_shortcut(self) -> None:
        c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
                    max_retries=10, verify_ssl=False)
        assert c.retry_config.max_retries == 10
        c.close()


class TestClientModels:
    def test_list_models(self, client: Client) -> None:
        models = client.list_models()
        assert models.object == "list"
        assert len(models.data) > 0

    def test_get_model_found(self, client: Client) -> None:
        m = client.get_model("mistral-7b")
        assert m is not None
        assert m.id == "mistral-7b"
        assert m.eu_safe is True

    def test_get_model_not_found(self, client: Client) -> None:
        m = client.get_model("nonexistent-model")
        assert m is None


class TestClientStats:
    def test_get_stats_default(self, client: Client) -> None:
        stats = client.get_stats()
        assert stats["total_requests"] == 0

    def test_telemetry_enabled(self) -> None:
        c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
                    telemetry=True, verify_ssl=False)
        assert c.telemetry.enabled is True
        c.close()


class TestClientLifecycle:
    def test_context_manager(self) -> None:
        with Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL,
                     verify_ssl=False) as c:
            assert c.http_client is not None

    def test_repr_masks_key(self) -> None:
        c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL, verify_ssl=False)
        r = repr(c)
        assert TEST_API_KEY not in r
        assert "sk-tes...def" in r
        c.close()

    def test_trailing_slash_stripped(self) -> None:
        c = Client(api_key=TEST_API_KEY, base_url=TEST_BASE_URL + "/",
                    verify_ssl=False)
        assert not c.route_url.endswith("//v1/route")
        c.close()
