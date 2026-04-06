/**
 * Sovereign AI — RGPD-compliant routing with PII detection.
 *
 * When PII is detected, the platform automatically routes to EU-only
 * providers (Scaleway, OVHCloud) with EU-safe models (Mistral, Llama, Gemma).
 *
 * Prerequisites:
 *   export AI_INFRA_API_KEY="sk-your-key-here"
 *   npx ts-node examples/sovereign.ts
 */

import { Client, RoutingMode, AIInfraError } from "../src";

async function main() {
  const client = new Client({
    mode: RoutingMode.EuOnly, // Force EU routing for all requests
    telemetry: true,
  });

  try {
    // Request with PII — server-side Presidio will detect it
    // and enforce EU-only routing automatically
    const response = await client.chat.completions.create({
      messages: [
        { role: "user", content: "Résume le dossier médical de Jean Dupont, né le 15/03/1985, IBAN FR76 1234 5678 9012" },
      ],
      pii_check: true, // Enable client-side PII warning
    });

    console.log(response.choices[0].message.content);
    console.log();
    console.log("--- Sovereignty Report ---");
    console.log(`EU routing:        ${response.savings.eu_routing}`);
    console.log(`Forced EU routing: ${response.savings.forced_eu_routing}`);
    console.log(`RGPD compliant:    ${response.savings.rgpd_compliant}`);
    console.log(`PII types found:   ${response.savings.pii_types_detected.join(", ") || "none"}`);
    console.log(`Provider:          ${response.savings.provider_used}`);
    console.log(`Model:             ${response.savings.model_used}`);
  } catch (error) {
    if (error instanceof AIInfraError) {
      console.error(`API Error: ${error.message} (status: ${error.statusCode})`);
    } else {
      throw error;
    }
  }

  // Check telemetry stats
  const stats = client.getStats();
  console.log();
  console.log("--- Telemetry ---");
  console.log(`Total requests: ${stats.totalRequests}`);
  console.log(`Total cost:     $${stats.totalCostUsd.toFixed(4)}`);
  console.log(`Total saved:    $${stats.totalSavingsUsd.toFixed(4)}`);
}

main().catch(console.error);
