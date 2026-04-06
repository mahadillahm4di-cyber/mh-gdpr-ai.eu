# AI Infrastructure Platform — TypeScript SDK

Official TypeScript/Node.js SDK for the AI Infrastructure Platform. Drop-in OpenAI replacement with intelligent GPU routing, cost optimization (30-70% savings), and RGPD-compliant sovereign AI.

## Installation

```bash
npm install ai-infra
```

**Requirements:** Node.js 18+ (uses native `fetch` and `crypto.randomUUID`).

## Quick Start

```typescript
import { Client } from "ai-infra";

const client = new Client({ apiKey: "sk-your-key" });

const response = await client.chat.completions.create({
  messages: [{ role: "user", content: "Hello!" }],
});

console.log(response.choices[0].message.content);
console.log(`Cost: $${response.savings.cost_usd} — Saved: ${response.savings.savings_percent}%`);
```

## Features

| Feature | Description |
|---|---|
| **OpenAI-compatible** | Same `client.chat.completions.create()` interface |
| **Cost optimization** | Auto-selects cheapest model/provider (30-70% savings) |
| **Sovereign routing** | PII detected → EU-only providers (Scaleway, OVH) |
| **24 models, 9 families** | Mistral, OpenAI, Anthropic, Llama, Google, Cohere, etc. |
| **Streaming** | Async iterator with real-time SSE parsing |
| **Retry + circuit breaker** | Exponential backoff, configurable thresholds |
| **Telemetry** | Local-only cost/latency tracking with callbacks |
| **Zero dependencies** | Uses native `fetch`, no external packages |

## Streaming

```typescript
const stream = await client.chat.completions.create({
  messages: [{ role: "user", content: "Write a poem" }],
  stream: true,
});

for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
}

// Routing metadata available after stream
console.log(stream.metadata); // { model, provider, estimated_cost_usd }
```

## Sovereign AI (RGPD)

```typescript
import { Client, RoutingMode } from "ai-infra";

const client = new Client({ mode: RoutingMode.EuOnly });

const response = await client.chat.completions.create({
  messages: [{ role: "user", content: "Jean Dupont, IBAN FR76..." }],
  pii_check: true, // Client-side PII warning
});

console.log(response.savings.eu_routing);         // true
console.log(response.savings.rgpd_compliant);      // true
console.log(response.savings.pii_types_detected);  // ["iban"]
```

## Routing Modes

```typescript
import { RoutingMode } from "ai-infra";

RoutingMode.BestCost         // Cheapest model and provider
RoutingMode.BestQuality      // Best model regardless of cost
RoutingMode.BestSpeed        // Lowest latency
RoutingMode.Balanced         // Cost/quality/speed balance
RoutingMode.BestAvailability // Most reliable provider
RoutingMode.EuOnly           // EU-only providers (RGPD)
```

## Error Handling

```typescript
import {
  Client,
  AuthenticationError,
  RateLimitError,
  BudgetExceededError,
  AIInfraError,
} from "ai-infra";

try {
  const response = await client.chat.completions.create({ ... });
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error("Invalid API key");
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited — retry after ${error.retryAfter}s`);
  } else if (error instanceof BudgetExceededError) {
    console.error("Monthly budget exhausted");
  } else if (error instanceof AIInfraError) {
    console.error(`${error.name}: ${error.message} (${error.statusCode})`);
  }
}
```

## Configuration

```typescript
const client = new Client({
  apiKey: "sk-...",                    // or AI_INFRA_API_KEY env var
  baseUrl: "https://api.ai-infra.io", // Custom endpoint
  mode: RoutingMode.BestCost,         // Default routing mode
  timeout: 60,                        // Request timeout (seconds)
  maxRetries: 3,                      // Retry attempts
  telemetry: true,                    // Enable local cost tracking
  onRequest: (metrics) => {           // Callback per request
    console.log(`${metrics.model}: $${metrics.costUsd}`);
  },
  retryConfig: {
    baseDelay: 0.5,                   // Initial retry delay (seconds)
    maxDelay: 30,                     // Max retry delay
    jitter: 0.25,                     // Random jitter
  },
  circuitBreakerConfig: {
    failureThreshold: 5,              // Failures before circuit opens
    recoveryTimeout: 30,              // Seconds before half-open
    successThreshold: 2,              // Successes to close circuit
  },
});
```

## Migration from OpenAI

```diff
- import OpenAI from "openai";
+ import { Client } from "ai-infra";

- const client = new OpenAI({ apiKey: "sk-..." });
+ const client = new Client({ apiKey: "sk-..." });

  const response = await client.chat.completions.create({
    messages: [{ role: "user", content: "Hello" }],
-   model: "gpt-4",
+   model: "auto", // Platform selects optimal model
  });

  console.log(response.choices[0].message.content);
+ console.log(`Saved: $${response.savings.cost_saved_usd}`);
```

## Available Models

24 models across 9 families. EU-safe models are RGPD-compliant:

| Model | Family | EU Safe | Use Case |
|---|---|---|---|
| mistral-7b | Mistral | Yes | Simple chat, Q&A |
| mixtral-8x7b | Mistral | Yes | Reasoning, long generation |
| codestral | Mistral | Yes | Code generation |
| mistral-large | Mistral | Yes | Complex analysis |
| llama-3-70b | Meta | Yes | Advanced reasoning |
| gpt-4o | OpenAI | No | Multi-modal |
| claude-3-opus | Anthropic | No | Deep analysis |
| ... | | | See `client.listModels()` |

## Development

```bash
npm install
npm test              # Run tests
npm run test:coverage # Coverage report (85% minimum)
npm run lint          # ESLint
npm run build         # Compile to dist/
```

## License

MIT
