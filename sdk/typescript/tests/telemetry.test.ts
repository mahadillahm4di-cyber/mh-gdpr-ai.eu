import { describe, it, expect, vi } from "vitest";
import { TelemetryCollector } from "../src/telemetry";
import type { RequestMetrics } from "../src/types";

function makeMetrics(overrides: Partial<RequestMetrics> = {}): RequestMetrics {
  return {
    model: "mistral-7b",
    latencyMs: 100,
    statusCode: 200,
    isStream: false,
    isCacheHit: false,
    costUsd: 0.001,
    savingsUsd: 0.005,
    ...overrides,
  };
}

describe("TelemetryCollector", () => {
  it("does not record when disabled", () => {
    const tel = new TelemetryCollector({ enabled: false });
    tel.record(makeMetrics());
    const stats = tel.getStats();
    expect(stats.totalRequests).toBe(0);
  });

  it("records metrics when enabled", () => {
    const tel = new TelemetryCollector({ enabled: true });
    tel.record(makeMetrics());
    tel.record(makeMetrics({ latencyMs: 200 }));

    const stats = tel.getStats();
    expect(stats.totalRequests).toBe(2);
    expect(stats.avgLatencyMs).toBe(150);
    expect(stats.totalCostUsd).toBeCloseTo(0.002);
    expect(stats.totalSavingsUsd).toBeCloseTo(0.01);
  });

  it("tracks errors", () => {
    const tel = new TelemetryCollector({ enabled: true });
    tel.record(makeMetrics({ statusCode: 200 }));
    tel.record(makeMetrics({ statusCode: 500 }));
    tel.record(makeMetrics({ statusCode: 429 }));

    const stats = tel.getStats();
    expect(stats.totalErrors).toBe(2);
    expect(stats.errorRate).toBeCloseTo(2 / 3);
  });

  it("tracks cache hits", () => {
    const tel = new TelemetryCollector({ enabled: true });
    tel.record(makeMetrics({ isCacheHit: true }));
    tel.record(makeMetrics({ isCacheHit: false }));

    expect(tel.getStats().cacheHitRate).toBe(0.5);
  });

  it("tracks stream rate", () => {
    const tel = new TelemetryCollector({ enabled: true });
    tel.record(makeMetrics({ isStream: true }));
    tel.record(makeMetrics({ isStream: false }));
    tel.record(makeMetrics({ isStream: true }));

    expect(tel.getStats().streamRate).toBeCloseTo(2 / 3);
  });

  it("calls onRequest callback", () => {
    const callback = vi.fn();
    const tel = new TelemetryCollector({ enabled: true, onRequest: callback });
    const metrics = makeMetrics();
    tel.record(metrics);

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith(metrics);
  });

  it("resets all counters", () => {
    const tel = new TelemetryCollector({ enabled: true });
    tel.record(makeMetrics());
    tel.record(makeMetrics());
    tel.reset();

    const stats = tel.getStats();
    expect(stats.totalRequests).toBe(0);
    expect(stats.totalCostUsd).toBe(0);
    expect(stats.totalSavingsUsd).toBe(0);
  });
});
