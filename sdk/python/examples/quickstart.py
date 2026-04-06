"""Quick start — get a response in 3 lines.

Run:
    export AI_INFRA_API_KEY="sk-your-key-here"
    python examples/quickstart.py
"""

from ai_infra import Client

# Create client (reads AI_INFRA_API_KEY from environment)
client = Client()

# Send a request — "auto" picks the best model for the task
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Explain quantum computing in 2 sentences."}],
)

# Print the response
print(response.choices[0].message.content)

# See how much you saved
print(f"\nModel used: {response.savings.model_used}")
print(f"Cost: ${response.savings.cost_usd:.4f}")
print(f"Saved: ${response.savings.cost_saved_usd:.4f} ({response.savings.savings_percent:.0f}%)")
