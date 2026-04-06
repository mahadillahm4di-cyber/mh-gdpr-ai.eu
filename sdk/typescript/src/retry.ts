/**
 * Retry logic with exponential backoff + circuit breaker.
 *
 * Mirrors the Python SDK retry module exactly:
 * - Exponential backoff with jitter
 * - Configurable retry/circuit breaker thresholds
 * - Three-state circuit breaker (CLOSED → OPEN → HALF_OPEN)
 */

import type { RetryConfig, CircuitBreakerConfig } from "./types";
import { AIInfraError, isRetryable } from "./errors";

// ── Defaults ───────────────────────────────────────────────────────────────────

export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 0.5,
  maxDelay: 30.0,
  jitter: 0.25,
  retryOnTimeout: true,
};

export const DEFAULT_CIRCUIT_BREAKER_CONFIG: CircuitBreakerConfig = {
  failureThreshold: 5,
  recoveryTimeout: 30.0,
  successThreshold: 2,
};

// ── Backoff ────────────────────────────────────────────────────────────────────

/**
 * Compute delay for a retry attempt.
 *
 * Formula: min(baseDelay * 2^attempt, maxDelay) + random(0, jitter)
 */
export function computeDelay(attempt: number, config: RetryConfig): number {
  const exponential = config.baseDelay * Math.pow(2, attempt);
  const capped = Math.min(exponential, config.maxDelay);
  const jitter = Math.random() * config.jitter;
  return capped + jitter;
}

/** Check if an error should be retried. */
export function shouldRetry(error: unknown, _config: RetryConfig): boolean {
  if (error instanceof AIInfraError) {
    return isRetryable(error);
  }
  // Network errors (TypeError from fetch) are retryable
  if (error instanceof TypeError) {
    return true;
  }
  return false;
}

/** Sleep for a given number of seconds. */
export function sleep(seconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, seconds * 1000));
}

// ── Circuit Breaker ────────────────────────────────────────────────────────────

export enum CircuitState {
  Closed = "CLOSED",
  Open = "OPEN",
  HalfOpen = "HALF_OPEN",
}

/**
 * Three-state circuit breaker.
 *
 * State transitions:
 *   CLOSED → OPEN:      After failureThreshold consecutive failures
 *   OPEN → HALF_OPEN:   After recoveryTimeout seconds
 *   HALF_OPEN → CLOSED: After successThreshold consecutive successes
 *   HALF_OPEN → OPEN:   On any failure
 */
export class CircuitBreaker {
  private _state: CircuitState = CircuitState.Closed;
  private _failureCount: number = 0;
  private _successCount: number = 0;
  private _lastFailureTime: number = 0;
  private readonly _config: CircuitBreakerConfig;

  constructor(config?: Partial<CircuitBreakerConfig>) {
    this._config = { ...DEFAULT_CIRCUIT_BREAKER_CONFIG, ...config };
  }

  /** Current circuit state. */
  get state(): CircuitState {
    // Auto-transition from OPEN → HALF_OPEN after recovery timeout
    if (this._state === CircuitState.Open) {
      const elapsed = (Date.now() - this._lastFailureTime) / 1000;
      if (elapsed >= this._config.recoveryTimeout) {
        this._state = CircuitState.HalfOpen;
        this._successCount = 0;
      }
    }
    return this._state;
  }

  /** Check if requests are allowed through. */
  get isAllowed(): boolean {
    const currentState = this.state; // triggers auto-transition
    return currentState !== CircuitState.Open;
  }

  /** Record a successful request. */
  recordSuccess(): void {
    if (this._state === CircuitState.HalfOpen) {
      this._successCount++;
      if (this._successCount >= this._config.successThreshold) {
        this._state = CircuitState.Closed;
        this._failureCount = 0;
        this._successCount = 0;
      }
    } else {
      this._failureCount = 0;
    }
  }

  /** Record a failed request. */
  recordFailure(): void {
    this._lastFailureTime = Date.now();

    if (this._state === CircuitState.HalfOpen) {
      // Any failure in half-open → back to open
      this._state = CircuitState.Open;
      this._successCount = 0;
    } else {
      this._failureCount++;
      if (this._failureCount >= this._config.failureThreshold) {
        this._state = CircuitState.Open;
      }
    }
  }

  /** Force-reset to closed state. */
  reset(): void {
    this._state = CircuitState.Closed;
    this._failureCount = 0;
    this._successCount = 0;
    this._lastFailureTime = 0;
  }
}
