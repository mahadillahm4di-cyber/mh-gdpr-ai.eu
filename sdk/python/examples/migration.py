"""Migration from OpenAI — zero code change required.

This example shows that existing OpenAI code works with the
AI Infrastructure SDK by changing only the import and base_url.

Run:
    export AI_INFRA_API_KEY="sk-your-key-here"
    python examples/migration.py
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BEFORE (OpenAI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# from openai import OpenAI
# client = OpenAI(api_key="sk-...")
#
# response = client.chat.completions.create(
#     model="gpt-4o",
#     messages=[{"role": "user", "content": "Hello!"}],
#     max_tokens=256,
#     temperature=0.7,
#     stream=False,
# )
# print(response.choices[0].message.content)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AFTER (AI Infrastructure) — 1 line changed
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from ai_infra import Client  # <-- Only this line changes

client = Client()  # Reads AI_INFRA_API_KEY from environment

# Exact same API call — no changes needed
response = client.chat.completions.create(
    model="gpt-4o",           # Same model names work
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=256,           # Same parameters
    temperature=0.7,          # Same parameters
    stream=False,             # Same parameters
)

# Same response structure
print(response.choices[0].message.content)
print(f"Model: {response.model}")
print(f"Tokens used: {response.usage.total_tokens}")

# Bonus: see your savings (not available with OpenAI)
print(f"\nSavings: ${response.savings.cost_saved_usd:.4f}")
print(f"Savings rate: {response.savings.savings_percent:.0f}%")
print(f"RGPD compliant: {response.savings.rgpd_compliant}")

# Bonus: use "auto" for intelligent model selection
response_auto = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "What is 2+2?"}],
)
print(f"\nAuto-selected model: {response_auto.savings.model_used}")
print(f"Cost: ${response_auto.savings.cost_usd:.6f} (vs fixed model)")

client.close()
