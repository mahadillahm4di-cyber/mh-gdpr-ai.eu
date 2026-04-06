# AI Infrastructure Python SDK

Drop-in replacement for the OpenAI Python client with **30-70% cost savings**,
RGPD-compliant routing, and real-time savings tracking.

## Installation

```bash
pip install ai-infra
```

## Quick Start

```python
from ai_infra import Client

client = Client(api_key="sk-...")
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
print(f"Saved: ${response.savings.cost_saved_usd:.4f}")
```

## Migration from OpenAI

Change **one line** — the rest of your code stays identical:

```python
# Before
from openai import OpenAI
client = OpenAI(api_key="sk-...")

# After
from ai_infra import Client
client = Client(api_key="sk-...")

# Same API — zero changes needed
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=256,
    temperature=0.7,
)
print(response.choices[0].message.content)
```

## Authentication

```python
# Option 1: Pass directly
client = Client(api_key="sk-...")

# Option 2: Environment variable (recommended)
# export AI_INFRA_API_KEY="sk-..."
client = Client()
```

## Routing Modes

```python
client = Client(mode="best_cost")       # Minimize cost (default behavior)
client = Client(mode="best_quality")    # Use the most capable model
client = Client(mode="best_speed")      # Lowest latency
client = Client(mode="balanced")        # Balance cost, quality, speed
client = Client(mode="eu_only")         # RGPD — EU providers only
```

Override per-request:

```python
response = client.chat.completions.create(
    model="auto",
    messages=[...],
    routing_mode="eu_only",
)
```

## Streaming

```python
stream = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Write a poem"}],
    stream=True,
)
with stream:
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
```

## Cost Tracking

Every response includes savings information:

```python
response = client.chat.completions.create(...)

print(response.savings.cost_usd)            # Actual cost
print(response.savings.cost_saved_usd)      # Amount saved vs retail
print(response.savings.savings_percent)     # Savings percentage
print(response.savings.model_used)          # Model selected
print(response.savings.provider_used)       # Provider used
print(response.savings.cache_hit)           # Whether response came from cache
print(response.savings.rgpd_compliant)      # RGPD compliance status
print(response.savings.eu_routing)          # Whether EU routing was used
print(response.savings.forced_eu_routing)   # Whether EU was forced by PII
print(response.savings.pii_types_detected)  # PII types found server-side
```

## RGPD Sovereign Routing

When PII is detected, the server automatically routes to EU providers:

```python
client = Client(mode="eu_only")
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Analyse le dossier de Jean Dupont"}],
    pii_check=True,   # Optional: client-side PII warning
)
assert response.savings.rgpd_compliant is True
```

## Client-Side PII Detection

```python
response = client.chat.completions.create(
    messages=[{"role": "user", "content": "Contact jean@example.com"}],
    pii_check=True,
)
# Emits: UserWarning: PII detected client-side: ['email']
```

## Model Listing

```python
models = client.list_models()
for model in models.data:
    print(f"{model.id} — EU safe: {model.eu_safe}, capabilities: {model.capabilities}")

# Get specific model
model = client.get_model("mistral-7b")
```

## Telemetry

Local-only aggregate stats (no data is sent externally):

```python
client = Client(telemetry=True)

# After some requests...
stats = client.get_stats()
print(stats["total_requests"])
print(stats["avg_latency_ms"])
print(stats["total_savings_usd"])
print(stats["cache_hit_rate"])

# Custom callback
def on_request(metrics):
    print(f"Request completed: {metrics.model} in {metrics.latency_ms}ms")

client = Client(telemetry=True, on_request=on_request)
```

## Error Handling

```python
from ai_infra import (
    AIInfraError,
    AuthenticationError,
    RateLimitError,
    BudgetExceededError,
    NoProviderAvailableError,
)

try:
    response = client.chat.completions.create(...)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited, retry after: {e.retry_after}s")
except BudgetExceededError:
    print("Monthly budget exhausted")
except NoProviderAvailableError:
    print("All providers down — try again later")
except AIInfraError as e:
    print(f"API error: {e.message} (status: {e.status_code})")
```

## Advanced Configuration

```python
from ai_infra import Client
from ai_infra.retry import RetryConfig, CircuitBreakerConfig

client = Client(
    api_key="sk-...",
    base_url="https://api.ai-infra.io",  # Custom endpoint
    timeout=30.0,                          # Request timeout
    max_retries=5,                         # Retry transient errors
    verify_ssl=True,                       # TLS verification
    proxy="http://proxy:8080",             # HTTP proxy
    ca_bundle="/path/to/ca.pem",           # Custom CA bundle
    retry_config=RetryConfig(
        max_retries=3,
        base_delay=0.5,
        max_delay=30.0,
    ),
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
    ),
)
```

## Supported Models

| Model | Capabilities | EU Safe |
|-------|-------------|---------|
| mistral-7b | chat | Yes |
| mixtral-8x7b | chat, reasoning | Yes |
| codestral | code | Yes |
| mistral-large | chat, reasoning | Yes |
| llama-3-70b | chat, reasoning | Yes |
| llama-3-8b | chat | Yes |
| gpt-4o | chat, reasoning | No |
| gpt-4-turbo | chat, reasoning | No |
| claude-3-opus | chat, reasoning | No |
| claude-3-sonnet | chat, reasoning | No |
| deepseek-v2 | chat, reasoning | No |
| qwen2-72b | chat, reasoning | No |
| *+ 12 more* | | |

Use `model="auto"` to let the router select the optimal model.

## FAQ

**Q: Is my API key safe?**
A: Yes. The SDK never logs, stores, or includes your API key in error
messages. Keys are validated at startup and masked in all outputs.

**Q: What happens when a provider goes down?**
A: The SDK includes a client-side circuit breaker that fails fast. The
server also maintains a provider fallback chain — if Scaleway is down,
it automatically tries OVHCloud, then other providers.

**Q: Is my data RGPD compliant?**
A: When PII is detected, the server forces routing through EU providers
(Scaleway, OVHCloud). Use `mode="eu_only"` or `pii_check=True` for
explicit control.

**Q: What TLS version is used?**
A: TLS 1.2 minimum, with TLS 1.3 preferred. Certificate verification
is enabled by default.

## License

MIT
