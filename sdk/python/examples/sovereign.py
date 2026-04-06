"""Sovereign AI — RGPD-compliant EU-only routing.

Forces all requests through EU providers (Scaleway, OVHCloud)
to guarantee data sovereignty.  PII is automatically detected
server-side and routed to EU providers even without this mode.

Run:
    export AI_INFRA_API_KEY="sk-your-key-here"
    python examples/sovereign.py
"""

from ai_infra import Client

# Create client with EU-only routing mode
client = Client(mode="eu_only")

# This request will ONLY use EU providers
response = client.chat.completions.create(
    model="auto",
    messages=[
        {"role": "user", "content": "Analyse ce contrat de travail pour Jean Dupont."},
    ],
    pii_check=True,  # Warn client-side if PII detected
)

print(response.choices[0].message.content)

# Verify sovereignty
print(f"\nProvider: {response.savings.provider_used}")
print(f"RGPD compliant: {response.savings.rgpd_compliant}")
print(f"EU routing: {response.savings.eu_routing}")
print(f"Forced EU routing (PII): {response.savings.forced_eu_routing}")
print(f"PII types detected: {response.savings.pii_types_detected}")
print(f"Cache hit: {response.savings.cache_hit}")
print(f"Model: {response.savings.model_used}")

# List EU-safe models
print("\nEU-safe models available:")
for model in client.list_models().data:
    if model.eu_safe:
        print(f"  - {model.id}")
