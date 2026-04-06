"""PII detection and masking examples.

Shows how to detect and mask personal data before sending to any LLM.
Run: python examples/pii_detection.py
"""

from sovereign_gateway import PIIDetector, PIIMasker

detector = PIIDetector(use_presidio=False)
masker = PIIMasker()

# --- Detect PII types ---
print("=" * 60)
print("PII Detection")
print("=" * 60)

texts = [
    "Send invoice to jean.dupont@company.fr",
    "Card: 4111 1111 1111 1111",
    "IBAN: FR76 3000 6000 0112 3456 7890 189",
    "Call +33 6 12 34 56 78 for details",
    "SSN: 123-45-6789",
    "NIR: 1 85 05 78 006 084 36",
    "Server IP: 192.168.1.42",
    "The weather is nice today",  # no PII
]

for text in texts:
    entities = detector.detect(text)
    if entities:
        types = [e.entity_type for e in entities]
        print(f"  [{', '.join(types)}] {text[:50]}...")
    else:
        print(f"  [CLEAN] {text[:50]}")

# --- Mask PII ---
print()
print("=" * 60)
print("PII Masking")
print("=" * 60)

messages = [
    "Contact jean@example.fr or call +33 6 12 34 56 78",
    "Payment to IBAN FR76 3000 6000 0112 3456 7890 189",
    "Cardholder: 4111 1111 1111 1111, SSN: 123-45-6789",
]

for msg in messages:
    masked, types = masker.mask(msg)
    print(f"\n  Original: {msg}")
    print(f"  Masked:   {masked}")
    print(f"  Types:    {types}")

# --- Quick check ---
print()
print("=" * 60)
print("Quick PII Check")
print("=" * 60)

print(f"  Has PII: {detector.has_pii('Email: test@company.com')}")  # True
print(f"  Has PII: {detector.has_pii('Hello, how are you?')}")       # False
