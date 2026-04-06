<p align="center">
  <img src="docs/assets/logo.svg" alt="mh-gdpr-ai.eu" width="200">
</p>

<h1 align="center">mh-gdpr-ai.eu</h1>

<p align="center">
  <strong>GDPR-compliant LLM routing with real-time PII detection</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#how-it-works">How It Works</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#examples">Examples</a> &bull;
  <a href="#api-reference">API Reference</a> &bull;
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <a href="https://github.com/mahadillahm4di-cyber/mh-gdpr-ai.eu/actions"><img src="https://img.shields.io/github/actions/workflow/status/mahadillahm4di-cyber/mh-gdpr-ai.eu/ci.yml?branch=master&style=flat-square&label=tests" alt="Tests"></a>
  <a href="https://pypi.org/project/mh-gdpr-ai/"><img src="https://img.shields.io/pypi/v/mh-gdpr-ai?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://pypi.org/project/mh-gdpr-ai/"><img src="https://img.shields.io/pypi/pyversions/mh-gdpr-ai?style=flat-square" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green?style=flat-square" alt="License"></a>
  <a href="https://github.com/mahadillahm4di-cyber/mh-gdpr-ai.eu/stargazers"><img src="https://img.shields.io/github/stars/mahadillahm4di-cyber/mh-gdpr-ai.eu?style=flat-square" alt="Stars"></a>
</p>

---

> **Your AI calls cross the Atlantic. Your users' data shouldn't.**
>
> If your LLM prompt contains a name, email, or IBAN — and it hits a US server — that's a GDPR violation.
> Max fine: **4% of global revenue or 20M EUR**.
>
> This gateway fixes that in **3 lines of code**.

---

## The Problem

Every time you call `openai.chat.completions.create()` with a European user's name in the prompt, you're potentially violating GDPR Article 44 (international data transfers).

```
Your EU User  -->  Your App  -->  OpenAI API (Virginia, US)  -->  GDPR VIOLATION
     |                                    |
     |          Name, email, IBAN         |
     |          in the prompt             |
     +------------------------------------+
              Personal data left the EU
```

**Most teams either:**
- A) Ignore it and hope for the best
- B) Route everything to EU (expensive)
- C) Anonymize all data (breaks context)

**We built option D:**

```
Your EU User  -->  Your App  -->  Sovereign Gateway  -->  PII detected?
                                       |                      |
                                       |              YES: EU provider only
                                       |              NO:  cheapest provider
                                       |
                                  100% GDPR compliant
                                  30-40% cheaper than option B
```

---

## Quick Start

### Install

```bash
pip install mh-gdpr-ai
```

### 3 Lines of Code

```python
from sovereign_gateway import SovereignGateway

gateway = SovereignGateway()
result = gateway.route([{"role": "user", "content": "Analyze the account of jean.dupont@company.fr"}])

print(result.pii_detected)       # True
print(result.pii_types)          # ['EMAIL_ADDRESS']
print(result.forced_eu_routing)  # True
print(result.gdpr_compliant)     # True
```

That's it. PII detected = EU only. No PII = cheapest provider.

---

## How It Works

The gateway runs a **3-filter pipeline** on every request in under 50ms:

```
                    ┌─────────────────────────────────────┐
                    │         INCOMING REQUEST             │
                    │  "Analyze jean.dupont@company.fr"    │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  FILTER 1: PII DETECTION             │
                    │                                      │
                    │  Layer 1: Presidio NLP               │
                    │    -> PERSON, EMAIL, PHONE, IBAN...  │
                    │                                      │
                    │  Layer 2: Regex (defense in depth)   │
                    │    -> EMAIL, CREDIT_CARD, SSN...     │
                    │                                      │
                    │  Result: EMAIL_ADDRESS detected      │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  FILTER 2: ROUTING DECISION          │
                    │                                      │
                    │  PII found?                          │
                    │  ├─ YES -> EU providers ONLY         │
                    │  │         (Scaleway, OVHCloud)      │
                    │  │         Cannot be bypassed.       │
                    │  │                                   │
                    │  └─ NO  -> Cheapest provider         │
                    │            (any region)              │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  FILTER 3: COMPLIANCE METADATA       │
                    │                                      │
                    │  {                                   │
                    │    "gdpr_compliant": true,           │
                    │    "pii_types": ["EMAIL_ADDRESS"],   │
                    │    "forced_eu_routing": true,        │
                    │    "provider": "scaleway"            │
                    │  }                                   │
                    │                                      │
                    │  Ready for your DPO's audit report.  │
                    └─────────────────────────────────────┘
```

### Dual-Layer PII Detection

| Layer | Engine | Speed | Entities | Purpose |
|-------|--------|-------|----------|---------|
| **Primary** | Microsoft Presidio (NLP) | ~30ms | 15+ types | High accuracy, context-aware |
| **Fallback** | Regex patterns | <5ms | 7 types | Guaranteed detection, always runs |

Both layers run on every request. If Presidio misses something, regex catches it. If Presidio isn't installed, regex handles everything.

---

## Features

### PII Detection (15+ Entity Types)

| Entity Type | Example | Detection |
|-------------|---------|-----------|
| `PERSON` | Jean Dupont | Presidio |
| `EMAIL_ADDRESS` | jean@company.fr | Presidio + Regex |
| `PHONE_NUMBER` | +33 6 12 34 56 78 | Presidio + Regex |
| `IBAN_CODE` | FR76 3000 6000 0112... | Presidio + Regex |
| `CREDIT_CARD` | 4111 1111 1111 1111 | Presidio + Regex |
| `US_SSN` | 123-45-6789 | Presidio + Regex |
| `FR_NIR` | 1 85 05 78 006 084 36 | Regex |
| `IP_ADDRESS` | 192.168.1.1 | Presidio + Regex |
| `LOCATION` | 14 Rue de Rivoli, Paris | Presidio |
| `DATE_TIME` | Born on 15/03/1985 | Presidio |
| `MEDICAL_LICENSE` | DEA: AB1234567 | Presidio |
| `CRYPTO` | 1A1zP1eP5QGefi2... | Presidio |
| `NRP` | French nationality | Presidio |
| `UK_NHS` | 943 476 5919 | Presidio |
| `US_PASSPORT` | 123456789 | Presidio |

### Sovereign Routing

| Condition | Routing | Providers | Model |
|-----------|---------|-----------|-------|
| PII detected | **EU ONLY** | Scaleway, OVHCloud | EU-safe (Mistral, Llama, Gemma) |
| No PII | **CHEAPEST** | Any provider | Any model |

### PII Masking

```python
from sovereign_gateway import PIIMasker

masker = PIIMasker()
masked, types = masker.mask("Email jean@company.fr, IBAN FR76 3000 6000 0112 3456 7890 189")

print(masked)  # "Email [EMAIL_REDACTED], IBAN [IBAN_REDACTED]"
print(types)   # ["EMAIL_ADDRESS", "IBAN_CODE"]
```

### Compliance-Ready Audit Logs

```python
result = gateway.route([{"role": "user", "content": "Patient Jean Dupont..."}])

# Ready for your DPO
print(result.compliance_summary)
# {
#     "gdpr_compliant": True,
#     "pii_detected": True,
#     "pii_types": ["PERSON"],
#     "routing_decision": "eu_only",
#     "provider_region": "EU",
#     "provider": "scaleway",
#     "model": "mistral-7b"
# }
```

---

## Examples

### Basic Routing

```python
from sovereign_gateway import SovereignGateway

gateway = SovereignGateway()

# PII detected -> EU forced
result = gateway.route([
    {"role": "user", "content": "Analyze the account of jean.dupont@company.fr"}
])
assert result.forced_eu_routing == True
assert result.gdpr_compliant == True

# No PII -> cheapest
result = gateway.route([
    {"role": "user", "content": "Summarize this quarterly report"}
])
assert result.forced_eu_routing == False
```

### FastAPI Integration

```python
from fastapi import FastAPI
from sovereign_gateway import SovereignGateway

app = FastAPI()
gateway = SovereignGateway()

@app.post("/v1/chat")
async def chat(messages: list[dict]):
    # Check routing before calling your LLM
    result = gateway.route(messages)

    if result.forced_eu_routing:
        # Call EU provider (Scaleway, OVHCloud)
        response = await call_eu_provider(messages, model=result.model_used)
    else:
        # Call cheapest provider
        response = await call_any_provider(messages)

    return {"response": response, "compliance": result.compliance_summary}
```

### PII Detection Only

```python
from sovereign_gateway import PIIDetector

detector = PIIDetector()

# Full entity detection
entities = detector.detect("Call Jean at +33 6 12 34 56 78")
for entity in entities:
    print(f"  {entity.entity_type} (confidence: {entity.score})")

# Quick check
if detector.has_pii(user_input):
    print("WARNING: PII detected in user input")
```

### Run Examples

```bash
python examples/basic_routing.py
python examples/pii_detection.py
```

---

## Installation Options

```bash
# Core (regex-only PII detection)
pip install mh-gdpr-ai

# With Presidio NLP (recommended for production)
pip install mh-gdpr-ai[presidio]

# With FastAPI support
pip install mh-gdpr-ai[api]

# Everything
pip install mh-gdpr-ai[all]
```

### With Presidio (Recommended)

Presidio adds NLP-based detection for entities that regex can't catch (person names, locations, dates). Install it for production use:

```bash
pip install mh-gdpr-ai[presidio]
python -m spacy download en_core_web_lg
```

```python
# Presidio is automatically used when installed
gateway = SovereignGateway()  # uses Presidio + regex

# Force regex-only (faster, fewer dependencies)
gateway = SovereignGateway(use_presidio=False)
```

---

## API Reference

### `SovereignGateway`

The main entry point.

| Method | Description | Returns |
|--------|-------------|---------|
| `route(messages, model?, request_id?)` | Analyze and route | `RouteResult` |
| `detect_pii(text)` | Detect PII types | `list[str]` |
| `has_pii(text)` | Quick PII check | `bool` |
| `mask(text)` | Mask PII in text | `str` |
| `mask_messages(messages)` | Mask PII in messages | `list[dict]` |

### `RouteResult`

| Field | Type | Description |
|-------|------|-------------|
| `decision` | `RoutingDecision` | `eu_only`, `cheapest`, or `cache_hit` |
| `pii_detected` | `bool` | Whether PII was found |
| `pii_types` | `list[str]` | Types of PII detected |
| `forced_eu_routing` | `bool` | Whether EU was forced |
| `gdpr_compliant` | `bool` | Whether the result is GDPR compliant |
| `model_used` | `str` | Selected model |
| `provider_used` | `str` | Selected provider |
| `latency_ms` | `float` | Processing time in ms |
| `compliance_summary` | `dict` | Audit-ready summary |

### `PIIDetector`

| Method | Description | Returns |
|--------|-------------|---------|
| `detect(text)` | Full entity detection | `list[PIIEntity]` |
| `detect_types(text)` | Type names only | `list[str]` |
| `has_pii(text)` | Quick boolean check | `bool` |

### `PIIMasker`

| Method | Description | Returns |
|--------|-------------|---------|
| `mask(text)` | Mask PII in text | `(str, list[str])` |
| `detect(text)` | Detect types (no mask) | `list[str]` |
| `mask_messages(messages)` | Mask across messages | `(list[dict], list[str])` |

---

## Supported Models

### EU-Safe Models (used when PII detected)

| Model | Family | Use Case |
|-------|--------|----------|
| `mistral-7b` | Mistral | Fast, cheap, general |
| `mixtral-8x7b` | Mistral | Reasoning, long context |
| `codestral` | Mistral | Code generation |
| `mistral-large` | Mistral | Complex analysis |
| `llama-3-70b` | Meta | High quality |
| `llama-3-8b` | Meta | Fast, efficient |
| `gemma-7b` | Google | Lightweight |

### All Supported Models

The gateway supports 20+ models across 9 families: Mistral, OpenAI, Anthropic, Meta, Google, Cohere, Microsoft, DeepSeek, and Alibaba.

---

## Architecture

```
mh-gdpr-ai.eu/
├── sovereign_gateway/          # Main package
│   ├── gateway.py              # SovereignGateway (main entry point)
│   ├── pii/
│   │   ├── detector.py         # Dual-layer PII detection
│   │   └── masker.py           # PII masking
│   ├── router/
│   │   └── sovereign.py        # Sovereign routing engine
│   └── models/
│       └── schemas.py          # Pydantic models
├── examples/                   # Working examples
│   ├── basic_routing.py
│   ├── pii_detection.py
│   └── fastapi_integration.py
├── tests/                      # Full test suite
│   ├── test_pii_detector.py
│   ├── test_masker.py
│   └── test_sovereign_router.py
├── pyproject.toml              # Package config
├── Dockerfile                  # Production container
└── Makefile                    # Dev commands
```

---

## Development

```bash
git clone https://github.com/mahadillahm4di-cyber/mh-gdpr-ai.eu.git
cd mh-gdpr-ai.eu

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

# Run tests
make test

# Run linter
make lint

# Run examples
make examples
```

---

## Why This Exists

GDPR Article 44 requires that personal data of EU residents stays within the EEA unless adequate safeguards exist. Most LLM API calls go to US servers. If your prompt contains a user's name, email, or IBAN — you're transferring personal data outside the EU.

**The fine is up to 4% of global annual revenue or 20 million EUR, whichever is higher.**

This gateway ensures that never happens, automatically.

---

## Roadmap

- [x] Regex-based PII detection (7 entity types)
- [x] Presidio NLP integration (15+ entity types)
- [x] Sovereign routing engine
- [x] PII masking
- [x] Compliance audit summaries
- [ ] Semantic cache integration
- [ ] LiteLLM provider integration
- [ ] Real-time dashboard
- [ ] GDPR compliance report generation (PDF)
- [ ] OpenAI SDK drop-in replacement

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

<p align="center">
  <strong>Built for teams who take data privacy seriously.</strong>
  <br>
  <sub>Star this repo if you think GDPR compliance shouldn't be an afterthought.</sub>
</p>
