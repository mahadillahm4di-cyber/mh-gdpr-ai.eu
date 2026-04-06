/**
 * Core type definitions for the AI Infrastructure SDK.
 *
 * All response types mirror the OpenAPI spec and Python SDK models exactly.
 * No `any` — every field is strictly typed.
 */

// ── Enums ──────────────────────────────────────────────────────────────────────

/** Available routing strategies for inference requests. */
export enum RoutingMode {
  BestCost = "best_cost",
  BestQuality = "best_quality",
  BestSpeed = "best_speed",
  Balanced = "balanced",
  BestAvailability = "best_availability",
  EuOnly = "eu_only",
}

// ── Chat Messages ──────────────────────────────────────────────────────────────

/** Valid roles for chat messages. */
export type MessageRole = "system" | "user" | "assistant";

/** A single chat message. */
export interface ChatMessage {
  role: MessageRole;
  content: string;
}

// ── Request Options ────────────────────────────────────────────────────────────

/** Options for creating a chat completion (non-streaming). */
export interface ChatCompletionCreateParams {
  model?: string;
  messages: ChatMessage[];
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  stream?: false;
  routing_mode?: RoutingMode | string;
  pii_check?: boolean;
}

/** Options for creating a streaming chat completion. */
export interface ChatCompletionStreamParams {
  model?: string;
  messages: ChatMessage[];
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  stream: true;
  routing_mode?: RoutingMode | string;
  pii_check?: boolean;
}

// ── Response Types ─────────────────────────────────────────────────────────────

/** Token usage statistics for a completion. */
export interface Usage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/** Cost savings and routing metadata — unique to AI Infrastructure Platform. */
export interface Savings {
  cost_usd: number;
  cost_saved_usd: number;
  savings_percent: number;
  model_used: string;
  provider_used: string;
  source: "inference" | "cache";
  cache_hit: boolean;
  latency_ms: number;
  rgpd_compliant: boolean;
  eu_routing: boolean;
  forced_eu_routing: boolean;
  pii_types_detected: string[];
}

/** A message in a completion choice. */
export interface ChoiceMessage {
  role: string;
  content: string;
}

/** A single completion choice. */
export interface Choice {
  index: number;
  message: ChoiceMessage;
  finish_reason: string | null;
}

/** Full chat completion response (non-streaming). */
export interface ChatCompletion {
  id: string;
  object: "chat.completion";
  created: number;
  model: string;
  choices: Choice[];
  usage: Usage;
  savings: Savings;
  request_id: string;
}

// ── Streaming Types ────────────────────────────────────────────────────────────

/** Delta content in a streaming chunk. */
export interface DeltaContent {
  role?: string;
  content?: string;
}

/** A single streaming choice. */
export interface StreamChoice {
  index: number;
  delta: DeltaContent;
  finish_reason: string | null;
}

/** A single streaming chunk (SSE event). */
export interface ChatCompletionChunk {
  id: string;
  object: "chat.completion.chunk";
  created: number;
  model: string;
  choices: StreamChoice[];
}

// ── Model Types ────────────────────────────────────────────────────────────────

/** Information about an available model. */
export interface ModelInfo {
  id: string;
  object: "model";
  owned_by: string;
  capabilities: string[];
  eu_safe: boolean;
}

/** List of available models. */
export interface ModelList {
  object: "list";
  data: ModelInfo[];
}

// ── Configuration Types ────────────────────────────────────────────────────────

/** Retry behavior configuration. */
export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  jitter: number;
  retryOnTimeout: boolean;
}

/** Circuit breaker configuration. */
export interface CircuitBreakerConfig {
  failureThreshold: number;
  recoveryTimeout: number;
  successThreshold: number;
}

/** Telemetry request metrics emitted after each request. */
export interface RequestMetrics {
  model: string;
  latencyMs: number;
  statusCode: number;
  isStream: boolean;
  isCacheHit: boolean;
  costUsd: number;
  savingsUsd: number;
}

/** Aggregated telemetry statistics. */
export interface TelemetryStats {
  totalRequests: number;
  totalErrors: number;
  errorRate: number;
  avgLatencyMs: number;
  totalCostUsd: number;
  totalSavingsUsd: number;
  cacheHitRate: number;
  streamRate: number;
}

/** Client constructor options. */
export interface ClientOptions {
  apiKey?: string;
  baseUrl?: string;
  mode?: RoutingMode | string;
  timeout?: number;
  maxRetries?: number;
  telemetry?: boolean;
  onRequest?: (metrics: RequestMetrics) => void;
  retryConfig?: Partial<RetryConfig>;
  circuitBreakerConfig?: Partial<CircuitBreakerConfig>;
}

// ── Streaming Metadata ─────────────────────────────────────────────────────────

/** Routing metadata extracted from SSE comment line. */
export interface StreamMetadata {
  request_id?: string;
  model?: string;
  provider?: string;
  estimated_cost_usd?: number;
  [key: string]: unknown;
}
