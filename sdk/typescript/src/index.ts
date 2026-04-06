/**
 * AI Infrastructure Platform — Official TypeScript SDK
 *
 * Intelligent GPU routing with cost optimization and RGPD-compliant sovereign AI.
 *
 * @example
 * ```typescript
 * import { Client, RoutingMode } from "ai-infra";
 *
 * const client = new Client({ apiKey: "sk-..." });
 *
 * // Simple completion
 * const response = await client.chat.completions.create({
 *   messages: [{ role: "user", content: "Explain quantum computing" }],
 * });
 * console.log(response.choices[0].message.content);
 * console.log(`Cost: $${response.savings.cost_usd} — Saved: ${response.savings.savings_percent}%`);
 *
 * // Streaming with EU-only routing
 * const stream = await client.chat.completions.create({
 *   messages: [{ role: "user", content: "Mon nom est Jean Dupont" }],
 *   stream: true,
 *   routing_mode: RoutingMode.EuOnly,
 * });
 * for await (const chunk of stream) {
 *   process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
 * }
 * ```
 *
 * @packageDocumentation
 */

// ── Client ─────────────────────────────────────────────────────────────────────
export { Client } from "./client";

// ── Chat ───────────────────────────────────────────────────────────────────────
export { Chat, Completions, StreamIterator } from "./chat";

// ── Types ──────────────────────────────────────────────────────────────────────
export {
  RoutingMode,
  type ChatMessage,
  type MessageRole,
  type ChatCompletionCreateParams,
  type ChatCompletionStreamParams,
  type ChatCompletion,
  type ChatCompletionChunk,
  type Choice,
  type ChoiceMessage,
  type StreamChoice,
  type DeltaContent,
  type Usage,
  type Savings,
  type ModelInfo,
  type ModelList,
  type StreamMetadata,
  type RetryConfig,
  type CircuitBreakerConfig,
  type RequestMetrics,
  type TelemetryStats,
  type ClientOptions,
} from "./types";

// ── Models ─────────────────────────────────────────────────────────────────────
export { AVAILABLE_MODELS } from "./models";

// ── Errors ─────────────────────────────────────────────────────────────────────
export {
  AIInfraError,
  AuthenticationError,
  SecurityBlockedError,
  PermissionError,
  RateLimitError,
  BudgetExceededError,
  ValidationError,
  ProviderError,
  NoProviderAvailableError,
  ConnectionError,
  TimeoutError,
} from "./errors";

// ── Utilities ──────────────────────────────────────────────────────────────────
export { detectPii, maskApiKey } from "./security";
