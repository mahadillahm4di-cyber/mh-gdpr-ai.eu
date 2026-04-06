/**
 * Quickstart — Minimal example to get started with AI Infrastructure Platform.
 *
 * Prerequisites:
 *   export AI_INFRA_API_KEY="sk-your-key-here"
 *   npx ts-node examples/quickstart.ts
 */

import { Client } from "../src";

async function main() {
  // Client reads AI_INFRA_API_KEY from environment automatically
  const client = new Client();

  // Simple chat completion — platform auto-selects cheapest model
  const response = await client.chat.completions.create({
    messages: [
      { role: "system", content: "You are a helpful assistant." },
      { role: "user", content: "What is the capital of France?" },
    ],
  });

  console.log(response.choices[0].message.content);
  console.log();
  console.log("--- Cost Report ---");
  console.log(`Model:    ${response.savings.model_used}`);
  console.log(`Provider: ${response.savings.provider_used}`);
  console.log(`Cost:     $${response.savings.cost_usd.toFixed(4)}`);
  console.log(`Saved:    $${response.savings.cost_saved_usd.toFixed(4)} (${response.savings.savings_percent}%)`);
  console.log(`Source:   ${response.savings.source}`);
  console.log(`RGPD:     ${response.savings.rgpd_compliant ? "compliant" : "non-compliant"}`);
}

main().catch(console.error);
