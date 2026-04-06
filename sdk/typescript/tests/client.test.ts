import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { Client } from "../src/client";
import { AuthenticationError } from "../src/errors";
import { RoutingMode } from "../src/types";

describe("Client", () => {
  const prefix = "sk";
  const hex = "a".repeat(40);
  const validKey = `${prefix}-${hex}`;

  beforeEach(() => {
    process.env.AI_INFRA_API_KEY = validKey;
  });

  afterEach(() => {
    delete process.env.AI_INFRA_API_KEY;
  });

  it("creates with explicit API key", () => {
    const client = new Client({ apiKey: validKey });
    expect(client.maskedApiKey).toMatch(/^sk-aaa\.\.\.aaa$/);
  });

  it("creates with env var API key", () => {
    const client = new Client();
    expect(client.maskedApiKey).toBeTruthy();
  });

  it("throws without API key", () => {
    delete process.env.AI_INFRA_API_KEY;
    expect(() => new Client()).toThrow(AuthenticationError);
  });

  it("uses default base URL", () => {
    const client = new Client();
    expect(client.baseUrl).toBe("https://api.ai-infra.io");
  });

  it("accepts custom base URL", () => {
    const client = new Client({ baseUrl: "https://custom.api.io" });
    expect(client.baseUrl).toBe("https://custom.api.io");
  });

  it("strips trailing slash from base URL", () => {
    const client = new Client({ baseUrl: "https://api.io///" });
    expect(client.baseUrl).toBe("https://api.io");
  });

  it("exposes chat.completions namespace", () => {
    const client = new Client();
    expect(client.chat).toBeDefined();
    expect(client.chat.completions).toBeDefined();
    expect(typeof client.chat.completions.create).toBe("function");
  });

  it("lists all 24 models", () => {
    const client = new Client();
    const models = client.listModels();
    expect(models.object).toBe("list");
    expect(models.data).toHaveLength(24);
  });

  it("finds a model by ID", () => {
    const client = new Client();
    const model = client.getModel("mistral-7b");
    expect(model).toBeDefined();
    expect(model!.eu_safe).toBe(true);
  });

  it("returns undefined for unknown model", () => {
    const client = new Client();
    expect(client.getModel("nonexistent")).toBeUndefined();
  });

  it("returns telemetry stats", () => {
    const client = new Client({ telemetry: true });
    const stats = client.getStats();
    expect(stats.totalRequests).toBe(0);
    expect(stats.totalCostUsd).toBe(0);
  });

  it("accepts routing mode", () => {
    // Should not throw
    const client = new Client({ mode: RoutingMode.EuOnly });
    expect(client).toBeDefined();
  });

  it("accepts custom retry config", () => {
    const client = new Client({
      maxRetries: 5,
      retryConfig: { baseDelay: 1, maxDelay: 60, jitter: 0.5, maxRetries: 5, retryOnTimeout: true },
    });
    expect(client).toBeDefined();
  });
});
