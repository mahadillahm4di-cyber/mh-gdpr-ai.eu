"""Tests for the Pydantic response models."""

from __future__ import annotations

from ai_infra.models import (
    AVAILABLE_MODELS,
    ChatCompletion,
    ChatCompletionChunk,
    ModelInfo,
    ModelList,
    RoutingMode,
    Savings,
    Usage,
)


class TestRoutingMode:
    def test_all_modes_exist(self) -> None:
        modes = {m.value for m in RoutingMode}
        assert "best_cost" in modes
        assert "best_quality" in modes
        assert "best_speed" in modes
        assert "balanced" in modes
        assert "eu_only" in modes
        assert "best_availability" in modes

    def test_string_enum(self) -> None:
        assert RoutingMode.EU_ONLY == "eu_only"


class TestUsage:
    def test_defaults(self) -> None:
        u = Usage()
        assert u.prompt_tokens == 0
        assert u.completion_tokens == 0
        assert u.total_tokens == 0

    def test_values(self) -> None:
        u = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        assert u.total_tokens == 30


class TestSavings:
    def test_defaults(self) -> None:
        s = Savings()
        assert s.cost_usd == 0.0
        assert s.rgpd_compliant is True
        assert s.eu_routing is False
        assert s.forced_eu_routing is False
        assert s.source == "inference"
        assert s.cache_hit is False
        assert s.pii_types_detected == []

    def test_idea1_cost_savings(self) -> None:
        s = Savings(
            cost_usd=0.001,
            cost_saved_usd=0.009,
            savings_percent=90.0,
            model_used="mistral-7b",
            provider_used="scaleway",
            source="cache",
            cache_hit=True,
        )
        assert s.cache_hit is True
        assert s.savings_percent == 90.0
        assert s.source == "cache"

    def test_idea2_sovereign_routing(self) -> None:
        s = Savings(
            rgpd_compliant=True,
            eu_routing=True,
            forced_eu_routing=True,
            pii_types_detected=["email", "phone"],
            provider_used="scaleway",
        )
        assert s.forced_eu_routing is True
        assert s.pii_types_detected == ["email", "phone"]
        assert s.rgpd_compliant is True

    def test_full(self) -> None:
        s = Savings(
            cost_usd=0.005,
            cost_saved_usd=0.010,
            savings_percent=66.7,
            model_used="mistral-7b",
            provider_used="scaleway",
            source="cache",
            cache_hit=True,
            rgpd_compliant=True,
            eu_routing=True,
            forced_eu_routing=True,
            pii_types_detected=["email"],
            latency_ms=50.0,
        )
        assert s.savings_percent == 66.7
        assert s.eu_routing is True


class TestChatCompletion:
    def test_from_api_response(self) -> None:
        data = {
            "request_id": "req-123",
            "content": "Hello!",
            "model": "mistral-7b",
            "provider": "scaleway",
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 10,
                "total_tokens": 15,
            },
            "source": "inference",
            "latency_ms": 200.0,
            "cost_usd": 0.001,
            "savings_percent": 60.0,
            "rgpd_compliant": True,
            "eu_routing": False,
        }
        result = ChatCompletion.from_api_response(data)

        assert result.id == "chatcmpl-req-123"
        assert result.object == "chat.completion"
        assert result.model == "mistral-7b"
        assert len(result.choices) == 1
        assert result.choices[0].message.role == "assistant"
        assert result.choices[0].message.content == "Hello!"
        assert result.choices[0].finish_reason == "stop"
        assert result.usage.total_tokens == 15
        assert result.savings.cost_usd == 0.001
        assert result.savings.savings_percent == 60.0
        assert result.savings.model_used == "mistral-7b"
        assert result.savings.provider_used == "scaleway"
        assert result.savings.cache_hit is False
        assert result.savings.forced_eu_routing is False
        assert result.savings.pii_types_detected == []
        assert result.request_id == "req-123"

    def test_from_api_response_cache(self) -> None:
        data = {
            "request_id": "req-cache",
            "content": "Cached!",
            "model": "mistral-7b",
            "provider": "cache",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "source": "cache",
            "latency_ms": 5.0,
            "cost_usd": 0.0,
            "savings_percent": 100.0,
        }
        result = ChatCompletion.from_api_response(data)
        assert result.savings.source == "cache"
        assert result.savings.cache_hit is True
        assert result.savings.cost_usd == 0.0

    def test_from_api_response_sovereign(self) -> None:
        data = {
            "request_id": "req-eu",
            "content": "EU response",
            "model": "mistral-7b",
            "provider": "scaleway",
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
            "source": "inference",
            "latency_ms": 200.0,
            "cost_usd": 0.002,
            "savings_percent": 50.0,
            "rgpd_compliant": True,
            "eu_routing": True,
            "forced_eu_routing": True,
            "pii_types_detected": ["email", "phone"],
        }
        result = ChatCompletion.from_api_response(data)
        assert result.savings.rgpd_compliant is True
        assert result.savings.eu_routing is True
        assert result.savings.forced_eu_routing is True
        assert result.savings.pii_types_detected == ["email", "phone"]

    def test_from_api_response_missing_fields(self) -> None:
        data = {"content": "Hi"}
        result = ChatCompletion.from_api_response(data)
        assert result.choices[0].message.content == "Hi"
        assert result.model == ""
        assert result.savings.cost_usd == 0.0


class TestChatCompletionChunk:
    def test_from_sse_data(self) -> None:
        data = {
            "id": "chatcmpl-abc",
            "object": "chat.completion.chunk",
            "created": 1700000000,
            "model": "mistral-7b",
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": "Hello"},
                "finish_reason": None,
            }],
        }
        chunk = ChatCompletionChunk.from_sse_data(data)
        assert chunk.id == "chatcmpl-abc"
        assert chunk.model == "mistral-7b"
        assert chunk.choices[0].delta.role == "assistant"
        assert chunk.choices[0].delta.content == "Hello"
        assert chunk.choices[0].finish_reason is None

    def test_from_sse_data_content_only(self) -> None:
        data = {
            "id": "chatcmpl-def",
            "object": "chat.completion.chunk",
            "created": 1700000000,
            "model": "mistral-7b",
            "choices": [{
                "index": 0,
                "delta": {"content": " world"},
                "finish_reason": None,
            }],
        }
        chunk = ChatCompletionChunk.from_sse_data(data)
        assert chunk.choices[0].delta.role is None
        assert chunk.choices[0].delta.content == " world"

    def test_from_sse_data_finish(self) -> None:
        data = {
            "id": "chatcmpl-ghi",
            "object": "chat.completion.chunk",
            "created": 1700000000,
            "model": "mistral-7b",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }],
        }
        chunk = ChatCompletionChunk.from_sse_data(data)
        assert chunk.choices[0].finish_reason == "stop"

    def test_from_sse_data_empty_choices(self) -> None:
        data = {"id": "x", "choices": []}
        chunk = ChatCompletionChunk.from_sse_data(data)
        assert chunk.choices == []


class TestModelInfo:
    def test_eu_safe_flag(self) -> None:
        m = ModelInfo(id="mistral-7b", eu_safe=True)
        assert m.eu_safe is True
        assert m.object == "model"

    def test_default_not_eu_safe(self) -> None:
        m = ModelInfo(id="gpt-4o")
        assert m.eu_safe is False


class TestModelList:
    def test_structure(self) -> None:
        ml = ModelList(data=[ModelInfo(id="test")])
        assert ml.object == "list"
        assert len(ml.data) == 1


class TestAvailableModels:
    def test_not_empty(self) -> None:
        assert len(AVAILABLE_MODELS) > 0

    def test_has_eu_safe_models(self) -> None:
        eu_safe = [m for m in AVAILABLE_MODELS if m.eu_safe]
        assert len(eu_safe) >= 8  # At least the 8 EU-safe models

    def test_all_have_capabilities(self) -> None:
        for m in AVAILABLE_MODELS:
            assert len(m.capabilities) > 0, f"{m.id} has no capabilities"

    def test_unique_ids(self) -> None:
        ids = [m.id for m in AVAILABLE_MODELS]
        assert len(ids) == len(set(ids))
