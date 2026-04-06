"""Cost tracking — see real-time savings vs OpenAI pricing.

Run:
    export AI_INFRA_API_KEY="sk-your-key-here"
    python examples/cost_tracking.py
"""

from ai_infra import Client

# Enable telemetry to track aggregate stats
client = Client(telemetry=True, mode="best_cost")

prompts = [
    "What is machine learning?",
    "Explain neural networks briefly.",
    "What are transformers in AI?",
    "How does gradient descent work?",
    "What is transfer learning?",
]

print("Sending 5 requests with best_cost routing...\n")

total_saved = 0.0
total_cost = 0.0

for prompt in prompts:
    response = client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
    )

    savings = response.savings
    total_cost += savings.cost_usd
    total_saved += savings.cost_saved_usd

    print(f"  {prompt[:40]:<40} | "
          f"model={savings.model_used:<15} | "
          f"${savings.cost_usd:.4f} | "
          f"saved ${savings.cost_saved_usd:.4f}")

# Print aggregate stats
print(f"\n{'='*70}")
print(f"Total cost:    ${total_cost:.4f}")
print(f"Total saved:   ${total_saved:.4f}")
if total_cost + total_saved > 0:
    pct = total_saved / (total_cost + total_saved) * 100
    print(f"Savings rate:  {pct:.1f}%")

# Show telemetry stats
stats = client.get_stats()
print("\nTelemetry stats:")
print(f"  Requests:      {stats['total_requests']:.0f}")
print(f"  Avg latency:   {stats['avg_latency_ms']:.0f}ms")
print(f"  Cache hit rate: {stats['cache_hit_rate']:.0%}")
print(f"  Error rate:    {stats['error_rate']:.0%}")

client.close()
