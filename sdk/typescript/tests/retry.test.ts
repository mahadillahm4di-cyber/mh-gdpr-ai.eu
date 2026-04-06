import { describe, it, expect, beforeEach } from "vitest";
import {
  computeDelay,
  shouldRetry,
  CircuitBreaker,
  CircuitState,
  DEFAULT_RETRY_CONFIG,
} from "../src/retry";
import {
  AIInfraError,
  AuthenticationError,
  RateLimitError,
  ConnectionError,
  ValidationError,
} from "../src/errors";

describe("computeDelay", () => {
  it("returns base delay for first attempt", () => {
    const delay = computeDelay(0, DEFAULT_RETRY_CONFIG);
    // base_delay=0.5, 2^0=1, so 0.5 + jitter(0..0.25)
    expect(delay).toBeGreaterThanOrEqual(0.5);
    expect(delay).toBeLessThanOrEqual(0.75);
  });

  it("doubles delay for each attempt", () => {
    const d0 = computeDelay(0, { ...DEFAULT_RETRY_CONFIG, jitter: 0 });
    const d1 = computeDelay(1, { ...DEFAULT_RETRY_CONFIG, jitter: 0 });
    const d2 = computeDelay(2, { ...DEFAULT_RETRY_CONFIG, jitter: 0 });
    expect(d1).toBe(d0 * 2);
    expect(d2).toBe(d0 * 4);
  });

  it("caps at maxDelay", () => {
    const config = { ...DEFAULT_RETRY_CONFIG, jitter: 0, maxDelay: 2.0 };
    const delay = computeDelay(10, config); // 0.5 * 2^10 = 512, capped at 2
    expect(delay).toBe(2.0);
  });
});

describe("shouldRetry", () => {
  it("retries RateLimitError", () => {
    expect(shouldRetry(new RateLimitError("x"), DEFAULT_RETRY_CONFIG)).toBe(
      true,
    );
  });

  it("retries ConnectionError", () => {
    expect(shouldRetry(new ConnectionError("x"), DEFAULT_RETRY_CONFIG)).toBe(
      true,
    );
  });

  it("does not retry AuthenticationError", () => {
    expect(
      shouldRetry(new AuthenticationError("x"), DEFAULT_RETRY_CONFIG),
    ).toBe(false);
  });

  it("does not retry ValidationError", () => {
    expect(shouldRetry(new ValidationError("x"), DEFAULT_RETRY_CONFIG)).toBe(
      false,
    );
  });

  it("retries TypeError (network error)", () => {
    expect(shouldRetry(new TypeError("fetch failed"), DEFAULT_RETRY_CONFIG)).toBe(
      true,
    );
  });
});

describe("CircuitBreaker", () => {
  let cb: CircuitBreaker;

  beforeEach(() => {
    cb = new CircuitBreaker({
      failureThreshold: 3,
      recoveryTimeout: 0.1, // 100ms for fast tests
      successThreshold: 2,
    });
  });

  it("starts in CLOSED state", () => {
    expect(cb.state).toBe(CircuitState.Closed);
    expect(cb.isAllowed).toBe(true);
  });

  it("stays CLOSED below failure threshold", () => {
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.state).toBe(CircuitState.Closed);
    expect(cb.isAllowed).toBe(true);
  });

  it("opens after failure threshold", () => {
    cb.recordFailure();
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.state).toBe(CircuitState.Open);
    expect(cb.isAllowed).toBe(false);
  });

  it("transitions OPEN → HALF_OPEN after recovery timeout", async () => {
    cb.recordFailure();
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.state).toBe(CircuitState.Open);

    // Wait for recovery
    await new Promise((r) => setTimeout(r, 150));
    expect(cb.state).toBe(CircuitState.HalfOpen);
    expect(cb.isAllowed).toBe(true);
  });

  it("transitions HALF_OPEN → CLOSED after success threshold", async () => {
    cb.recordFailure();
    cb.recordFailure();
    cb.recordFailure();
    await new Promise((r) => setTimeout(r, 150));

    expect(cb.state).toBe(CircuitState.HalfOpen);
    cb.recordSuccess();
    cb.recordSuccess();
    expect(cb.state).toBe(CircuitState.Closed);
  });

  it("transitions HALF_OPEN → OPEN on any failure", async () => {
    cb.recordFailure();
    cb.recordFailure();
    cb.recordFailure();
    await new Promise((r) => setTimeout(r, 150));

    expect(cb.state).toBe(CircuitState.HalfOpen);
    cb.recordFailure();
    expect(cb.state).toBe(CircuitState.Open);
  });

  it("resets to CLOSED", () => {
    cb.recordFailure();
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.state).toBe(CircuitState.Open);

    cb.reset();
    expect(cb.state).toBe(CircuitState.Closed);
    expect(cb.isAllowed).toBe(true);
  });

  it("resets failure count on success in CLOSED state", () => {
    cb.recordFailure();
    cb.recordFailure();
    cb.recordSuccess(); // resets count
    cb.recordFailure();
    cb.recordFailure();
    // Only 2 failures since last success, not 3 → still closed
    expect(cb.state).toBe(CircuitState.Closed);
  });
});
