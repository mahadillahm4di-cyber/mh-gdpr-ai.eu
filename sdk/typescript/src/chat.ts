/**
 * Chat completions — non-streaming and streaming.
 *
 * Provides the `client.chat.completions.create()` API that mirrors
 * OpenAI's interface while adding cost tracking and sovereign routing.
 */

import type {
  ChatCompletion,
  ChatCompletionChunk,
  ChatCompletionCreateParams,
  ChatCompletionStreamParams,
  StreamMetadata,
  RetryConfig,
} from "./types";
import { parseChatCompletion, parseChatCompletionChunk } from "./models";
import {
  AIInfraError,
  ConnectionError,
  TimeoutError,
  fromStatusCode,
} from "./errors";
import {
  computeDelay,
  shouldRetry,
  sleep,
  CircuitBreaker,
} from "./retry";
import { validateMessages, detectPii } from "./security";
import { TelemetryCollector } from "./telemetry";

// ── Stream Iterator ────────────────────────────────────────────────────────────

/**
 * Async iterator over SSE streaming chunks.
 *
 * The first SSE comment line (`:`) contains routing metadata as JSON.
 * Data lines contain ChatCompletionChunk objects.
 * Stream terminates with `data: [DONE]`.
 */
export class StreamIterator implements AsyncIterable<ChatCompletionChunk> {
  private _metadata: StreamMetadata = {};
  private _response: Response;
  private _done: boolean = false;

  constructor(response: Response) {
    this._response = response;
  }

  /** Routing metadata extracted from the SSE comment line. */
  get metadata(): StreamMetadata {
    return this._metadata;
  }

  async *[Symbol.asyncIterator](): AsyncIterator<ChatCompletionChunk> {
    if (!this._response.body) {
      return;
    }

    const reader = this._response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (!this._done) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed === "") continue;

          // SSE comment — contains routing metadata
          if (trimmed.startsWith(":")) {
            const jsonStr = trimmed.slice(1).trim();
            if (jsonStr) {
              try {
                this._metadata = JSON.parse(jsonStr) as StreamMetadata;
              } catch {
                // Not JSON metadata, ignore
              }
            }
            continue;
          }

          // SSE data line
          if (trimmed.startsWith("data:")) {
            const data = trimmed.slice(5).trim();
            if (data === "[DONE]") {
              this._done = true;
              break;
            }
            try {
              const parsed = JSON.parse(data) as Record<string, unknown>;
              yield parseChatCompletionChunk(parsed);
            } catch {
              // Malformed chunk, skip
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}

// ── Completions Namespace ──────────────────────────────────────────────────────

export class Completions {
  private _routeUrl: string;
  private _authHeaders: Record<string, string>;
  private _routingMode: string | undefined;
  private _timeout: number;
  private _retryConfig: RetryConfig;
  private _circuitBreaker: CircuitBreaker;
  private _telemetry: TelemetryCollector;

  constructor(options: {
    routeUrl: string;
    authHeaders: Record<string, string>;
    routingMode?: string;
    timeout: number;
    retryConfig: RetryConfig;
    circuitBreaker: CircuitBreaker;
    telemetry: TelemetryCollector;
  }) {
    this._routeUrl = options.routeUrl;
    this._authHeaders = options.authHeaders;
    this._routingMode = options.routingMode;
    this._timeout = options.timeout;
    this._retryConfig = options.retryConfig;
    this._circuitBreaker = options.circuitBreaker;
    this._telemetry = options.telemetry;
  }

  /** Create a chat completion (streaming or non-streaming). */
  async create(params: ChatCompletionCreateParams): Promise<ChatCompletion>;
  async create(params: ChatCompletionStreamParams): Promise<StreamIterator>;
  async create(
    params: ChatCompletionCreateParams | ChatCompletionStreamParams,
  ): Promise<ChatCompletion | StreamIterator> {
    // Validate messages
    const validatedMessages = validateMessages(params.messages);

    // Client-side PII warning
    if (params.pii_check) {
      for (const msg of validatedMessages) {
        const piiTypes = detectPii(msg.content);
        if (piiTypes.length > 0) {
          console.warn(
            `[ai-infra] PII detected in message (${msg.role}): ${piiTypes.join(", ")}. ` +
              "Server-side sovereign routing will enforce EU-only providers.",
          );
        }
      }
    }

    // Build request body
    const requestId = crypto.randomUUID();
    const body: Record<string, unknown> = {
      messages: validatedMessages,
      max_tokens: params.max_tokens ?? 1024,
      temperature: params.temperature ?? 0.7,
      top_p: params.top_p ?? 1.0,
      stream: params.stream ?? false,
      request_id: requestId,
    };

    if (params.model && params.model !== "auto") {
      body.model = params.model;
    }

    const mode = params.routing_mode ?? this._routingMode;
    if (mode) {
      body.routing_mode = mode;
    }

    // Execute with retry
    const startTime = Date.now();
    const response = await this._executeWithRetry(body, params.stream ?? false);
    const latencyMs = Date.now() - startTime;

    // Streaming response
    if (params.stream) {
      return new StreamIterator(response);
    }

    // Non-streaming response
    const data = (await response.json()) as Record<string, unknown>;
    const completion = parseChatCompletion(data);

    // Record telemetry
    this._telemetry.record({
      model: completion.model,
      latencyMs,
      statusCode: response.status,
      isStream: false,
      isCacheHit: completion.savings.cache_hit,
      costUsd: completion.savings.cost_usd,
      savingsUsd: completion.savings.cost_saved_usd,
    });

    return completion;
  }

  /** Execute HTTP request with retry logic and circuit breaker. */
  private async _executeWithRetry(
    body: Record<string, unknown>,
    stream: boolean,
  ): Promise<Response> {
    let lastError: AIInfraError | undefined;

    for (let attempt = 0; attempt <= this._retryConfig.maxRetries; attempt++) {
      // Circuit breaker check
      if (!this._circuitBreaker.isAllowed) {
        throw new AIInfraError("Circuit breaker is open — requests are temporarily blocked.", {
          statusCode: 503,
        });
      }

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(
          () => controller.abort(),
          this._timeout * 1000,
        );

        const response = await fetch(this._routeUrl, {
          method: "POST",
          headers: {
            ...this._authHeaders,
            Accept: stream ? "text/event-stream" : "application/json",
          },
          body: JSON.stringify(body),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        // Success
        if (response.ok) {
          this._circuitBreaker.recordSuccess();
          return response;
        }

        // HTTP error
        const errorBody = await response.text();
        const requestId = (body.request_id as string) ?? undefined;
        lastError = fromStatusCode(response.status, errorBody, requestId);
        this._circuitBreaker.recordFailure();

        // Record error telemetry
        this._telemetry.record({
          model: (body.model as string) ?? "auto",
          latencyMs: 0,
          statusCode: response.status,
          isStream: stream,
          isCacheHit: false,
          costUsd: 0,
          savingsUsd: 0,
        });

        // Check if retryable
        if (!shouldRetry(lastError, this._retryConfig)) {
          throw lastError;
        }
      } catch (error: unknown) {
        if (error instanceof AIInfraError) {
          lastError = error;
          if (!shouldRetry(error, this._retryConfig)) {
            throw error;
          }
        } else if (error instanceof Error && error.name === "AbortError") {
          lastError = new TimeoutError(
            `Request timed out after ${this._timeout}s`,
            { timeoutSeconds: this._timeout },
          );
          this._circuitBreaker.recordFailure();
        } else if (error instanceof TypeError) {
          // Network error (DNS, TLS, etc.)
          lastError = new ConnectionError(
            `Connection failed: ${(error as Error).message}`,
          );
          this._circuitBreaker.recordFailure();
        } else {
          throw error;
        }
      }

      // Wait before retry (skip on last attempt)
      if (attempt < this._retryConfig.maxRetries) {
        const delay = computeDelay(attempt, this._retryConfig);
        await sleep(delay);
      }
    }

    throw lastError ?? new AIInfraError("Max retries exceeded");
  }
}

// ── Chat Namespace ─────────────────────────────────────────────────────────────

export class Chat {
  readonly completions: Completions;

  constructor(completions: Completions) {
    this.completions = completions;
  }
}
