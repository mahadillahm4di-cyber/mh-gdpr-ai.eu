/**
 * Main client for the AI Infrastructure Platform.
 *
 * Usage:
 *   import { Client } from "ai-infra";
 *
 *   const client = new Client({ apiKey: "sk-..." });
 *   const response = await client.chat.completions.create({
 *     messages: [{ role: "user", content: "Hello" }],
 *   });
 *   console.log(response.choices[0].message.content);
 *   console.log(`Saved: $${response.savings.cost_saved_usd}`);
 */

import type {
  ClientOptions,
  ModelInfo,
  ModelList,
  RetryConfig,
  TelemetryStats,
} from "./types";
import { Chat, Completions } from "./chat";
import { resolveApiKey, maskApiKey } from "./security";
import { DEFAULT_RETRY_CONFIG, CircuitBreaker } from "./retry";
import { TelemetryCollector } from "./telemetry";
import { listModels, getModel } from "./models";

const SDK_VERSION = "1.0.0";
const DEFAULT_BASE_URL = "https://api.ai-infra.io";
const DEFAULT_TIMEOUT = 60;

export class Client {
  /** Chat completions namespace — mirrors OpenAI's `client.chat.completions`. */
  readonly chat: Chat;

  private _apiKey: string;
  private _baseUrl: string;
  private _telemetry: TelemetryCollector;
  private _circuitBreaker: CircuitBreaker;

  constructor(options?: ClientOptions) {
    this._apiKey = resolveApiKey(options?.apiKey);
    this._baseUrl = (options?.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");

    const timeout = options?.timeout ?? DEFAULT_TIMEOUT;
    const retryConfig: RetryConfig = {
      ...DEFAULT_RETRY_CONFIG,
      ...(options?.retryConfig ?? {}),
      maxRetries: options?.maxRetries ?? DEFAULT_RETRY_CONFIG.maxRetries,
    };

    this._circuitBreaker = new CircuitBreaker(options?.circuitBreakerConfig);
    this._telemetry = new TelemetryCollector({
      enabled: options?.telemetry,
      onRequest: options?.onRequest,
    });

    const routeUrl = `${this._baseUrl}/v1/route`;
    const authHeaders: Record<string, string> = {
      Authorization: `Bearer ${this._apiKey}`,
      "X-API-Key": this._apiKey,
      "Content-Type": "application/json",
      "User-Agent": `ai-infra-typescript/${SDK_VERSION}`,
    };

    const routingMode = options?.mode as string | undefined;

    const completions = new Completions({
      routeUrl,
      authHeaders,
      routingMode,
      timeout,
      retryConfig,
      circuitBreaker: this._circuitBreaker,
      telemetry: this._telemetry,
    });

    this.chat = new Chat(completions);
  }

  /** List all available models (24 models, 9 families). */
  listModels(): ModelList {
    return listModels();
  }

  /** Get info about a specific model by ID. */
  getModel(modelId: string): ModelInfo | undefined {
    return getModel(modelId);
  }

  /** Get local telemetry statistics (cost, latency, cache hit rate). */
  getStats(): TelemetryStats {
    return this._telemetry.getStats();
  }

  /** Masked API key for safe logging. */
  get maskedApiKey(): string {
    return maskApiKey(this._apiKey);
  }

  /** Base URL this client is connected to. */
  get baseUrl(): string {
    return this._baseUrl;
  }
}
