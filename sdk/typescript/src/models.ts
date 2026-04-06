/**
 * Available models catalog and response constructors.
 *
 * All 24 models across 9 families — matches the Python SDK and OpenAPI spec.
 */

import type {
  ModelInfo,
  ModelList,
  ChatCompletion,
  ChatCompletionChunk,
  Usage,
  Savings,
} from "./types";

/** Complete catalog of available models. */
export const AVAILABLE_MODELS: ModelInfo[] = [
  // Mistral (EU-safe)
  { id: "mistral-7b", object: "model", owned_by: "mistral", capabilities: ["chat"], eu_safe: true },
  { id: "mixtral-8x7b", object: "model", owned_by: "mistral", capabilities: ["chat", "reasoning"], eu_safe: true },
  { id: "codestral", object: "model", owned_by: "mistral", capabilities: ["code"], eu_safe: true },
  { id: "mistral-large", object: "model", owned_by: "mistral", capabilities: ["chat", "reasoning"], eu_safe: true },
  { id: "mistral-embed", object: "model", owned_by: "mistral", capabilities: ["embeddings"], eu_safe: true },
  // Meta / Llama (EU-safe)
  { id: "llama-3-70b", object: "model", owned_by: "meta", capabilities: ["chat", "reasoning"], eu_safe: true },
  { id: "llama-3-8b", object: "model", owned_by: "meta", capabilities: ["chat"], eu_safe: true },
  { id: "codellama-34b", object: "model", owned_by: "meta", capabilities: ["code"], eu_safe: true },
  // Google (EU-safe)
  { id: "gemma-7b", object: "model", owned_by: "google", capabilities: ["chat"], eu_safe: true },
  { id: "gemini-pro", object: "model", owned_by: "google", capabilities: ["chat", "reasoning"], eu_safe: false },
  // OpenAI
  { id: "gpt-4o", object: "model", owned_by: "openai", capabilities: ["chat", "reasoning"], eu_safe: false },
  { id: "gpt-4-turbo", object: "model", owned_by: "openai", capabilities: ["chat", "reasoning"], eu_safe: false },
  { id: "gpt-3.5-turbo", object: "model", owned_by: "openai", capabilities: ["chat"], eu_safe: false },
  // Anthropic
  { id: "claude-3-opus", object: "model", owned_by: "anthropic", capabilities: ["chat", "reasoning"], eu_safe: false },
  { id: "claude-3-sonnet", object: "model", owned_by: "anthropic", capabilities: ["chat", "reasoning"], eu_safe: false },
  { id: "claude-3-haiku", object: "model", owned_by: "anthropic", capabilities: ["chat"], eu_safe: false },
  // Cohere
  { id: "command-r-plus", object: "model", owned_by: "cohere", capabilities: ["chat", "reasoning"], eu_safe: false },
  { id: "command-r", object: "model", owned_by: "cohere", capabilities: ["chat"], eu_safe: false },
  // Microsoft
  { id: "phi-3-medium", object: "model", owned_by: "microsoft", capabilities: ["chat"], eu_safe: false },
  { id: "phi-3-mini", object: "model", owned_by: "microsoft", capabilities: ["chat"], eu_safe: false },
  // DeepSeek
  { id: "deepseek-v2", object: "model", owned_by: "deepseek", capabilities: ["chat", "reasoning"], eu_safe: false },
  { id: "deepseek-coder", object: "model", owned_by: "deepseek", capabilities: ["code"], eu_safe: false },
  // Alibaba
  { id: "qwen2-72b", object: "model", owned_by: "alibaba", capabilities: ["chat", "reasoning"], eu_safe: false },
  { id: "qwen2-7b", object: "model", owned_by: "alibaba", capabilities: ["chat"], eu_safe: false },
];

/** Build a ModelList response. */
export function listModels(): ModelList {
  return { object: "list", data: AVAILABLE_MODELS };
}

/** Find a model by ID. */
export function getModel(modelId: string): ModelInfo | undefined {
  return AVAILABLE_MODELS.find((m) => m.id === modelId);
}

// ── Default response values ────────────────────────────────────────────────────

const DEFAULT_USAGE: Usage = {
  prompt_tokens: 0,
  completion_tokens: 0,
  total_tokens: 0,
};

const DEFAULT_SAVINGS: Savings = {
  cost_usd: 0,
  cost_saved_usd: 0,
  savings_percent: 0,
  model_used: "",
  provider_used: "",
  source: "inference",
  cache_hit: false,
  latency_ms: 0,
  rgpd_compliant: true,
  eu_routing: false,
  forced_eu_routing: false,
  pii_types_detected: [],
};

/**
 * Parse a raw API JSON response into a typed ChatCompletion.
 * Applies defaults for any missing fields.
 */
export function parseChatCompletion(data: Record<string, unknown>): ChatCompletion {
  return {
    id: (data.id as string) ?? "",
    object: "chat.completion",
    created: (data.created as number) ?? Math.floor(Date.now() / 1000),
    model: (data.model as string) ?? "",
    choices: Array.isArray(data.choices)
      ? data.choices.map((c: Record<string, unknown>, i: number) => ({
          index: (c.index as number) ?? i,
          message: {
            role: ((c.message as Record<string, unknown>)?.role as string) ?? "assistant",
            content: ((c.message as Record<string, unknown>)?.content as string) ?? "",
          },
          finish_reason: (c.finish_reason as string) ?? "stop",
        }))
      : [],
    usage: { ...DEFAULT_USAGE, ...(data.usage as Partial<Usage>) },
    savings: { ...DEFAULT_SAVINGS, ...(data.savings as Partial<Savings>) },
    request_id: (data.request_id as string) ?? "",
  };
}

/**
 * Parse a raw SSE data JSON into a typed ChatCompletionChunk.
 */
export function parseChatCompletionChunk(data: Record<string, unknown>): ChatCompletionChunk {
  return {
    id: (data.id as string) ?? "",
    object: "chat.completion.chunk",
    created: (data.created as number) ?? Math.floor(Date.now() / 1000),
    model: (data.model as string) ?? "",
    choices: Array.isArray(data.choices)
      ? data.choices.map((c: Record<string, unknown>, i: number) => ({
          index: (c.index as number) ?? i,
          delta: {
            role: ((c.delta as Record<string, unknown>)?.role as string) ?? undefined,
            content: ((c.delta as Record<string, unknown>)?.content as string) ?? undefined,
          },
          finish_reason: (c.finish_reason as string) ?? null,
        }))
      : [],
  };
}
