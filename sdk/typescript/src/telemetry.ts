/**
 * Local-only telemetry — aggregates cost, latency, and cache metrics.
 *
 * No data is ever transmitted externally. Strictly local counters.
 * Mirrors the Python SDK telemetry module.
 */

import type { RequestMetrics, TelemetryStats } from "./types";

export class TelemetryCollector {
  private _enabled: boolean;
  private _onRequest: ((metrics: RequestMetrics) => void) | null;
  private _totalRequests: number = 0;
  private _totalErrors: number = 0;
  private _totalLatencyMs: number = 0;
  private _totalCostUsd: number = 0;
  private _totalSavingsUsd: number = 0;
  private _cacheHits: number = 0;
  private _streamRequests: number = 0;

  constructor(options?: {
    enabled?: boolean;
    onRequest?: (metrics: RequestMetrics) => void;
  }) {
    this._enabled =
      options?.enabled ??
      (process.env.AI_INFRA_TELEMETRY === "1" || false);
    this._onRequest = options?.onRequest ?? null;
  }

  /** Whether telemetry collection is active. */
  get enabled(): boolean {
    return this._enabled;
  }

  /** Record metrics from a completed request. */
  record(metrics: RequestMetrics): void {
    if (!this._enabled) return;

    this._totalRequests++;
    this._totalLatencyMs += metrics.latencyMs;
    this._totalCostUsd += metrics.costUsd;
    this._totalSavingsUsd += metrics.savingsUsd;

    if (metrics.statusCode >= 400) {
      this._totalErrors++;
    }
    if (metrics.isCacheHit) {
      this._cacheHits++;
    }
    if (metrics.isStream) {
      this._streamRequests++;
    }

    if (this._onRequest) {
      this._onRequest(metrics);
    }
  }

  /** Get aggregated statistics. */
  getStats(): TelemetryStats {
    const total = this._totalRequests || 1; // avoid division by zero
    return {
      totalRequests: this._totalRequests,
      totalErrors: this._totalErrors,
      errorRate: this._totalErrors / total,
      avgLatencyMs: this._totalLatencyMs / total,
      totalCostUsd: this._totalCostUsd,
      totalSavingsUsd: this._totalSavingsUsd,
      cacheHitRate: this._cacheHits / total,
      streamRate: this._streamRequests / total,
    };
  }

  /** Reset all counters to zero. */
  reset(): void {
    this._totalRequests = 0;
    this._totalErrors = 0;
    this._totalLatencyMs = 0;
    this._totalCostUsd = 0;
    this._totalSavingsUsd = 0;
    this._cacheHits = 0;
    this._streamRequests = 0;
  }
}
