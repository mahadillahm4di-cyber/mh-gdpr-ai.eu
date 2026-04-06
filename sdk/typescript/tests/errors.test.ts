import { describe, it, expect } from "vitest";
import {
  AIInfraError,
  AuthenticationError,
  RateLimitError,
  BudgetExceededError,
  ValidationError,
  SecurityBlockedError,
  PermissionError,
  ProviderError,
  NoProviderAvailableError,
  ConnectionError,
  TimeoutError,
  fromStatusCode,
  isRetryable,
} from "../src/errors";

describe("AIInfraError", () => {
  it("carries message, statusCode, and requestId", () => {
    const err = new AIInfraError("test error", {
      statusCode: 500,
      requestId: "req-123",
    });
    expect(err.message).toBe("test error");
    expect(err.statusCode).toBe(500);
    expect(err.requestId).toBe("req-123");
    expect(err.name).toBe("AIInfraError");
    expect(err).toBeInstanceOf(Error);
  });

  it("defaults statusCode and requestId to null", () => {
    const err = new AIInfraError("bare error");
    expect(err.statusCode).toBeNull();
    expect(err.requestId).toBeNull();
  });
});

describe("Specific error types", () => {
  it("AuthenticationError has status 401", () => {
    const err = new AuthenticationError("bad key");
    expect(err.statusCode).toBe(401);
    expect(err.name).toBe("AuthenticationError");
    expect(err).toBeInstanceOf(AIInfraError);
  });

  it("RateLimitError has status 429 and retryAfter", () => {
    const err = new RateLimitError("slow down", { retryAfter: 30 });
    expect(err.statusCode).toBe(429);
    expect(err.retryAfter).toBe(30);
  });

  it("RateLimitError defaults retryAfter to 60", () => {
    const err = new RateLimitError("slow down");
    expect(err.retryAfter).toBe(60);
  });

  it("BudgetExceededError has status 402", () => {
    const err = new BudgetExceededError("out of budget");
    expect(err.statusCode).toBe(402);
  });

  it("ValidationError has status 400", () => {
    const err = new ValidationError("bad input");
    expect(err.statusCode).toBe(400);
  });

  it("SecurityBlockedError has status 403", () => {
    const err = new SecurityBlockedError("blocked");
    expect(err.statusCode).toBe(403);
  });

  it("PermissionError has status 403", () => {
    const err = new PermissionError("no scope");
    expect(err.statusCode).toBe(403);
  });

  it("ProviderError has status 502 and provider name", () => {
    const err = new ProviderError("gpu fail", { provider: "scaleway" });
    expect(err.statusCode).toBe(502);
    expect(err.provider).toBe("scaleway");
  });

  it("ProviderError defaults provider to unknown", () => {
    const err = new ProviderError("gpu fail");
    expect(err.provider).toBe("unknown");
  });

  it("NoProviderAvailableError has status 503", () => {
    const err = new NoProviderAvailableError("all down");
    expect(err.statusCode).toBe(503);
  });

  it("ConnectionError has null statusCode", () => {
    const err = new ConnectionError("dns fail");
    expect(err.statusCode).toBeNull();
  });

  it("TimeoutError has null statusCode and timeoutSeconds", () => {
    const err = new TimeoutError("too slow", { timeoutSeconds: 30 });
    expect(err.statusCode).toBeNull();
    expect(err.timeoutSeconds).toBe(30);
  });
});

describe("fromStatusCode", () => {
  it("maps 401 to AuthenticationError", () => {
    const err = fromStatusCode(401, "invalid key", "req-1");
    expect(err).toBeInstanceOf(AuthenticationError);
    expect(err.requestId).toBe("req-1");
  });

  it("maps 402 to BudgetExceededError", () => {
    expect(fromStatusCode(402, "budget")).toBeInstanceOf(BudgetExceededError);
  });

  it("maps 403 to SecurityBlockedError", () => {
    expect(fromStatusCode(403, "blocked")).toBeInstanceOf(SecurityBlockedError);
  });

  it("maps 429 to RateLimitError", () => {
    expect(fromStatusCode(429, "limit")).toBeInstanceOf(RateLimitError);
  });

  it("maps 502 to ProviderError", () => {
    expect(fromStatusCode(502, "upstream")).toBeInstanceOf(ProviderError);
  });

  it("maps 503 to NoProviderAvailableError", () => {
    expect(fromStatusCode(503, "unavailable")).toBeInstanceOf(
      NoProviderAvailableError,
    );
  });

  it("falls back to AIInfraError for unmapped codes", () => {
    const err = fromStatusCode(418, "teapot");
    expect(err).toBeInstanceOf(AIInfraError);
    expect(err.statusCode).toBe(418);
  });
});

describe("isRetryable", () => {
  it("returns false for AuthenticationError", () => {
    expect(isRetryable(new AuthenticationError("x"))).toBe(false);
  });

  it("returns false for BudgetExceededError", () => {
    expect(isRetryable(new BudgetExceededError("x"))).toBe(false);
  });

  it("returns false for ValidationError", () => {
    expect(isRetryable(new ValidationError("x"))).toBe(false);
  });

  it("returns false for SecurityBlockedError", () => {
    expect(isRetryable(new SecurityBlockedError("x"))).toBe(false);
  });

  it("returns false for PermissionError", () => {
    expect(isRetryable(new PermissionError("x"))).toBe(false);
  });

  it("returns true for RateLimitError", () => {
    expect(isRetryable(new RateLimitError("x"))).toBe(true);
  });

  it("returns true for ConnectionError", () => {
    expect(isRetryable(new ConnectionError("x"))).toBe(true);
  });

  it("returns true for TimeoutError", () => {
    expect(isRetryable(new TimeoutError("x"))).toBe(true);
  });

  it("returns true for NoProviderAvailableError", () => {
    expect(isRetryable(new NoProviderAvailableError("x"))).toBe(true);
  });

  it("returns true for 500+ status codes", () => {
    expect(isRetryable(new AIInfraError("x", { statusCode: 500 }))).toBe(true);
    expect(isRetryable(new AIInfraError("x", { statusCode: 504 }))).toBe(true);
  });

  it("returns false for 400-level non-retryable", () => {
    expect(isRetryable(new AIInfraError("x", { statusCode: 404 }))).toBe(
      false,
    );
  });
});
