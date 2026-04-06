/**
 * Streaming — Real-time token streaming with cost tracking.
 *
 * Prerequisites:
 *   export AI_INFRA_API_KEY="sk-your-key-here"
 *   npx ts-node examples/streaming.ts
 */

import { Client } from "../src";

async function main() {
  const client = new Client();

  const stream = await client.chat.completions.create({
    messages: [
      { role: "user", content: "Write a haiku about cloud computing." },
    ],
    stream: true,
    max_tokens: 256,
  });

  // Stream tokens to stdout in real-time
  for await (const chunk of stream) {
    const content = chunk.choices[0]?.delta?.content;
    if (content) {
      process.stdout.write(content);
    }
  }
  console.log();

  // Routing metadata (model, provider, estimated cost) is available after stream
  console.log("\n--- Stream Metadata ---");
  console.log(`Model:    ${stream.metadata.model ?? "unknown"}`);
  console.log(`Provider: ${stream.metadata.provider ?? "unknown"}`);
  console.log(`Est cost: $${stream.metadata.estimated_cost_usd?.toFixed(4) ?? "N/A"}`);
}

main().catch(console.error);
