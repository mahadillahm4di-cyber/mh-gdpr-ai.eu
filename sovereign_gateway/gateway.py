"""SovereignGateway — main entry point for the GDPR-compliant AI gateway.

Two modes:
1. gateway.route()    — PII detection + routing decision (no LLM call)
2. gateway.complete() — PII detection + routing + actual LLM call end-to-end

Example (decision only):
    gateway = SovereignGateway()
    result = gateway.route([{"role": "user", "content": "jean@co.fr"}])
    print(result.forced_eu_routing)  # True

Example (end-to-end with real LLM):
    gateway = SovereignGateway(
        providers={"scaleway": {"api_key": "scw-xxx"}}
    )
    result = gateway.complete([{"role": "user", "content": "Hello jean@bnp.fr"}])
    print(result.content)             # Real LLM response
    print(result.forced_eu_routing)   # True (PII -> EU only)
"""

from __future__ import annotations

import time

import structlog

from sovereign_gateway.models.schemas import (
    CompletionResult,
    Message,
    RouteResult,
    SupportedModel,
)
from sovereign_gateway.pii.detector import PIIDetector
from sovereign_gateway.pii.masker import PIIMasker
from sovereign_gateway.providers.openai_compat import (
    OpenAICompatClient,
    ProviderConfig,
    load_providers_from_env,
)
from sovereign_gateway.router.sovereign import SovereignRouter

logger = structlog.get_logger(__name__)


class SovereignGateway:
    """GDPR-compliant AI gateway with automatic PII detection and EU routing.

    Args:
        pii_score_threshold: Minimum confidence for PII detection (0.0-1.0).
        use_presidio: Enable Presidio NLP detection.
        providers: Dict of provider configs. Keys are provider names,
            values are dicts with "api_key" and optionally "base_url".
            If not provided, reads from env vars.

    Example:
        gateway = SovereignGateway(providers={
            "scaleway": {"api_key": "scw-xxx"},
            "together_ai": {"api_key": "tok-xxx"},
        })
        result = gateway.complete([
            {"role": "user", "content": "Analyze jean.dupont@bnp.fr"}
        ])
        print(result.content)           # Real LLM response
        print(result.forced_eu_routing) # True
    """

    def __init__(
        self,
        pii_score_threshold: float = 0.5,
        use_presidio: bool = True,
        providers: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self._detector = PIIDetector(
            score_threshold=pii_score_threshold,
            use_presidio=use_presidio,
        )
        self._masker = PIIMasker()
        self._router = SovereignRouter(pii_detector=self._detector)
        self._client = OpenAICompatClient()
        self._log = logger.bind(component="sovereign_gateway")

        self._providers: dict[str, ProviderConfig] = {}
        if providers:
            self._providers = self._parse_provider_configs(providers)
        else:
            self._providers = load_providers_from_env()

    def complete(
        self,
        messages: list[dict[str, str]] | list[Message],
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> CompletionResult:
        """Detect PII, route to the right provider, and call the LLM.

        End-to-end: PII scan -> routing -> LLM call -> response.

        Args:
            messages: Chat messages as dicts or Message objects.
            model: Optional model preference (e.g., "mistral-7b").
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            CompletionResult with LLM response and compliance flags.

        Raises:
            RuntimeError: If no providers are configured.
            httpx.HTTPStatusError: If the provider API returns an error.
        """
        start = time.monotonic()

        msg_dicts = self._normalize_to_dicts(messages)
        route = self.route(messages, model=model)

        provider = self._select_provider(
            route.provider_used,
            route.forced_eu_routing,
        )

        response = self._client.call(
            config=provider,
            model=route.model_used,
            messages=msg_dicts,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = ""
        tokens_used = 0
        choices = response.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
        usage = response.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)

        latency = (time.monotonic() - start) * 1000

        self._log.info(
            "completion_done",
            provider=provider.name,
            model=route.model_used,
            pii_detected=route.pii_detected,
            eu_routed=route.forced_eu_routing,
            tokens=tokens_used,
            latency_ms=round(latency, 2),
        )

        return CompletionResult(
            content=content,
            model_used=route.model_used,
            provider_used=provider.name,
            forced_eu_routing=route.forced_eu_routing,
            gdpr_compliant=route.gdpr_compliant,
            pii_detected=route.pii_detected,
            pii_types=route.pii_types,
            latency_ms=round(latency, 2),
            tokens_used=tokens_used,
        )

    def route(
        self,
        messages: list[dict[str, str]] | list[Message],
        model: str | SupportedModel | None = None,
        request_id: str = "",
    ) -> RouteResult:
        """Analyze messages for PII and return a routing decision (no LLM call).

        Use complete() for end-to-end routing + LLM call.
        """
        normalized: list[Message] = []
        for msg in messages:
            if isinstance(msg, Message):
                normalized.append(msg)
            else:
                normalized.append(
                    Message(
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                    )
                )

        model_hint: SupportedModel | None = None
        if model is not None:
            if isinstance(model, SupportedModel):
                model_hint = model
            else:
                try:
                    model_hint = SupportedModel(model)
                except ValueError:
                    self._log.warning("unknown_model", model=model)

        return self._router.analyze_and_route(
            messages=normalized,
            model_hint=model_hint,
            request_id=request_id,
        )

    def detect_pii(self, text: str) -> list[str]:
        """Detect PII types in text."""
        return self._detector.detect_types(text)

    def has_pii(self, text: str) -> bool:
        """Quick check: does the text contain any PII?"""
        return self._detector.has_pii(text)

    def mask(self, text: str) -> str:
        """Mask all PII in text with safe placeholders."""
        masked, _ = self._masker.mask(text)
        return masked

    def mask_messages(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Mask PII in all chat messages."""
        masked, _ = self._masker.mask_messages(messages)
        return masked

    @property
    def providers(self) -> dict[str, ProviderConfig]:
        """Currently configured providers."""
        return dict(self._providers)

    def _select_provider(
        self,
        preferred: str,
        eu_only: bool,
    ) -> ProviderConfig:
        """Select the best available provider."""
        if not self._providers:
            raise RuntimeError(
                "No providers configured. Pass providers= to SovereignGateway() "
                "or set environment variables (e.g., SCALEWAY_API_KEY).\n"
                "See: https://github.com/mahadillahm4di-cyber/mh-gdpr-ai.eu#quick-start"
            )

        if preferred in self._providers:
            cfg = self._providers[preferred]
            if not eu_only or cfg.is_eu:
                return cfg

        candidates = sorted(self._providers.values(), key=lambda p: p.priority)

        if eu_only:
            eu_candidates = [p for p in candidates if p.is_eu]
            if eu_candidates:
                return eu_candidates[0]
            raise RuntimeError(
                "PII detected but no EU provider configured. "
                "Add: SCALEWAY_API_KEY or OVHCLOUD_API_KEY."
            )

        return candidates[0]

    def _normalize_to_dicts(
        self,
        messages: list[dict[str, str]] | list[Message],
    ) -> list[dict[str, str]]:
        """Convert messages to dicts for the API call."""
        result: list[dict[str, str]] = []
        for msg in messages:
            if isinstance(msg, Message):
                result.append({"role": msg.role, "content": msg.content})
            else:
                result.append(msg)
        return result

    @staticmethod
    def _parse_provider_configs(
        raw: dict[str, dict[str, str]],
    ) -> dict[str, ProviderConfig]:
        """Parse provider config dicts into ProviderConfig objects."""
        from sovereign_gateway.providers.openai_compat import _PROVIDER_BASE_URLS

        eu_providers = {"scaleway", "ovhcloud"}
        priorities = {
            "scaleway": 1,
            "ovhcloud": 2,
            "runpod": 3,
            "lambda_labs": 4,
            "together_ai": 5,
            "openai": 6,
            "litellm": 7,
        }

        configs: dict[str, ProviderConfig] = {}
        for name, params in raw.items():
            api_key = params.get("api_key", "")
            if not api_key:
                continue
            base_url = params.get(
                "base_url",
                _PROVIDER_BASE_URLS.get(name, ""),
            )
            configs[name] = ProviderConfig(
                name=name,
                api_key=api_key,
                base_url=base_url,
                is_eu=name in eu_providers,
                priority=priorities.get(name, 99),
            )

        return configs
