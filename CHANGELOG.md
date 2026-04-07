# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-07

### Added

- `gateway.complete()` — end-to-end method: PII detection + sovereign routing + LLM API call in one step
- OpenAI-compatible provider client — works with Scaleway, OVHcloud, Together AI, OpenAI, Mistral, DeepSeek, Groq, Fireworks, and any `/v1/chat/completions` endpoint
- `CompletionResult` model with LLM response content + full compliance metadata
- Provider configuration via constructor (`providers={"scaleway": {"api_key": "..."}}`) or environment variables (`SCALEWAY_API_KEY`)
- Automatic model name resolution per provider (e.g., `mistral-7b` maps to `mistralai/Mistral-7B-Instruct-v0.3` on Together AI)
- Provider fallback: if preferred provider unavailable, selects next best by priority
- 13 new tests for complete(), provider selection, and error handling (63 total)
- `httpx` added as core dependency for provider HTTP calls

### Changed

- `gateway.route()` is now documented as "decision only" (no LLM call) — use `complete()` for end-to-end

## [0.1.0] - 2026-04-06

### Added

- Dual-layer PII detection: Microsoft Presidio (NLP) + regex fallback
- 15+ PII entity types: PERSON, EMAIL, PHONE, IBAN, CREDIT_CARD, SSN, NIR, IP, and more
- Sovereign routing engine: PII detected = EU-only (Scaleway, OVHCloud), no PII = cheapest provider
- PII masking with type-specific placeholders (`[EMAIL_REDACTED]`, `[IBAN_REDACTED]`, etc.)
- Compliance-ready audit summaries for DPO reports
- FastAPI integration example
- Full test suite (50 tests)
- CI/CD with GitHub Actions (Python 3.10-3.13 + Presidio)
- Production Dockerfile (multi-stage, non-root, healthcheck)
- Support for 20+ models across 9 families (Mistral, OpenAI, Anthropic, Meta, Google, Cohere, DeepSeek, etc.)

### Security

- PII content is never logged — only types and counts
- EU routing cannot be bypassed via API when PII is detected
- Defense-in-depth: both Presidio and regex run on every request

[0.2.0]: https://github.com/mahadillahm4di-cyber/mh-gdpr-ai.eu/releases/tag/v0.2.0
[0.1.0]: https://github.com/mahadillahm4di-cyber/mh-gdpr-ai.eu/releases/tag/v0.1.0
