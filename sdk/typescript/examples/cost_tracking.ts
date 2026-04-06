/**
 * Cost Tracking — Monitor spending and savings in real-time.
 *
 * Uses the telemetry callback to log every request's cost and savings.
 *
 * Prerequisites:
 *   export AI_INFRA_API_KEY="sk-your-key-here"
 *   npx ts-node examples/cost_tracking.ts
 */

import { Client, type RequestMetrics } from "../src";

function onRequest(metrics: RequestMetrics): void {
  const tag = metrics.isCacheHit ? "[CACHE]" : "[INFER]";
  console.log(
    `${tag} ${metrics.model} | ` +
      `${metrics.latencyMs}ms | ` +
      `$${metrics.costUsd.toFixed(4)} cost | ` +
      `$${metrics.savingsUsd.toFixed(4)} saved`,
  );
}

async function main() {
  const client = new Client({
    telemetry: true,
    onRequest, // Called after every request
  });

  // Send multiple requests to accumulate stats
  const prompts = [
    "What is 2+2?",
    "Explain DNS in one sentence.",
    "What is 2+2?", // Likely cache hit
    "Translate 'hello' to French.",
  ];

  for (const prompt of prompts) {
    const response = await client.chat.completions.create({
      messages: [{ role: "user", content: prompt }],
    });
    console.log(`  → ${response.choices[0].message.content.slice(0, 80)}`);
    console.log();
  }

  // Final stats
  const stats = client.getStats();
  console.log("═══════════════════════════════════════");
  console.log("         Cost Tracking Summary");
  console.log("═══════════════════════════════════════");
  console.log(`Total requests:  ${stats.totalRequests}`);
  console.log(`Total cost:      $${stats.totalCostUsd.toFixed(4)}`);
  console.log(`Total saved:     $${stats.totalSavingsUsd.toFixed(4)}`);
  console.log(`Cache hit rate:  ${(stats.cacheHitRate * 100).toFixed(1)}%`);
  console.log(`Avg latency:     ${stats.avgLatencyMs.toFixed(0)}ms`);
  console.log(`Error rate:      ${(stats.errorRate * 100).toFixed(1)}%`);
}

main().catch(console.error);
