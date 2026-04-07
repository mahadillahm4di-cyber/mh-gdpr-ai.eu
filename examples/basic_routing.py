"""Basic sovereign routing example.

Demonstrates how the gateway detects PII and forces EU routing.

- route()    = decision only (no LLM call) — works without API keys
- complete() = end-to-end (PII scan + routing + LLM call) — requires provider keys

Run: python examples/basic_routing.py
"""

from sovereign_gateway import SovereignGateway

gateway = SovereignGateway(use_presidio=False)  # regex-only for this demo

# --- Example 1: PII detected → EU routing forced ---
print("=" * 60)
print("Example 1: Message with PII (email)")
print("=" * 60)

result = gateway.route(
    [
        {"role": "user", "content": "Please analyze the account of jean.dupont@company.fr"},
    ]
)

print(f"  PII detected:      {result.pii_detected}")
print(f"  PII types:         {result.pii_types}")
print(f"  Forced EU routing: {result.forced_eu_routing}")
print(f"  GDPR compliant:    {result.gdpr_compliant}")
print(f"  Decision:          {result.decision.value}")
print(f"  Provider:          {result.provider_used}")
print(f"  Latency:           {result.latency_ms}ms")
print()

# --- Example 2: No PII → cheapest routing ---
print("=" * 60)
print("Example 2: Message without PII")
print("=" * 60)

result = gateway.route(
    [
        {"role": "user", "content": "Summarize the key points of this quarterly report."},
    ]
)

print(f"  PII detected:      {result.pii_detected}")
print(f"  Forced EU routing: {result.forced_eu_routing}")
print(f"  Decision:          {result.decision.value}")
print(f"  Provider:          {result.provider_used}")
print()

# --- Example 3: Multiple PII types ---
print("=" * 60)
print("Example 3: Multiple PII types in one message")
print("=" * 60)

result = gateway.route(
    [
        {
            "role": "user",
            "content": (
                "Patient Jean Dupont (jean@hospital.fr) has IBAN "
                "FR76 3000 6000 0112 3456 7890 189. Please process the refund."
            ),
        }
    ]
)

print(f"  PII detected:      {result.pii_detected}")
print(f"  PII types:         {result.pii_types}")
print(f"  Entity count:      {result.pii_entity_count}")
print(f"  Forced EU routing: {result.forced_eu_routing}")
print(f"  GDPR compliant:    {result.gdpr_compliant}")
print()

# --- Example 4: Compliance summary for audit ---
print("=" * 60)
print("Example 4: Compliance summary (for your DPO)")
print("=" * 60)

summary = result.compliance_summary
for key, value in summary.items():
    print(f"  {key}: {value}")

# --- Example 5: End-to-end with complete() ---
print()
print("=" * 60)
print("Example 5: End-to-end LLM call (requires provider API keys)")
print("=" * 60)
print()
print("  # To use complete(), configure providers:")
print("  #")
print("  # gateway = SovereignGateway(providers={")
print('  #     "scaleway": {"api_key": "scw-..."},   # EU provider')
print('  #     "together_ai": {"api_key": "tok-..."},  # non-EU fallback')
print("  # })")
print("  #")
print('  # result = gateway.complete([{"role": "user", "content": "Hello"}])')
print("  # print(result.content)        # actual LLM response")
print("  # print(result.provider_used)  # which provider handled it")
print("  # print(result.pii_detected)   # was PII found?")
print("  # print(result.gdpr_compliant) # always True")
print()
print("  Set SCALEWAY_API_KEY or TOGETHER_AI_API_KEY env vars,")
print("  then see examples/fastapi_integration.py for a full API server.")
