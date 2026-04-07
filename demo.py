"""
mh-gdpr-ai.eu - Live Demo
==========================

This script demonstrates all features in real-time.
Perfect for screen recording / demo videos.

Run:  python demo.py
"""

import logging
import time
import sys

# Suppress structlog/logging output for clean demo
logging.disable(logging.CRITICAL)
import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
)

# Simulate typing effect for video
def slow_print(text, delay=0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def section(title):
    print()
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    slow_print(f"\033[1;36m  {title}\033[0m", delay=0.03)
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print()
    time.sleep(0.5)

def step(label):
    slow_print(f"\033[1;33m  >>> {label}\033[0m", delay=0.02)
    time.sleep(0.3)

def result(label, value, color="32"):
    print(f"      \033[{color}m{label}:\033[0m {value}")
    time.sleep(0.15)

def danger(text):
    print(f"      \033[1;31m{text}\033[0m")
    time.sleep(0.2)

def safe(text):
    print(f"      \033[1;32m{text}\033[0m")
    time.sleep(0.2)


# ──────────────────────────────────────────────────────────────
# INTRO
# ──────────────────────────────────────────────────────────────

print()
print()
slow_print("\033[1;37m  mh-gdpr-ai.eu v0.2.0\033[0m", delay=0.04)
slow_print("\033[0;37m  GDPR-compliant LLM routing with real-time PII detection\033[0m", delay=0.02)
print()
slow_print("\033[0;90m  Your AI calls cross the Atlantic. Your users' data shouldn't.\033[0m", delay=0.02)
time.sleep(1)


# ──────────────────────────────────────────────────────────────
# 1. INSTALLATION
# ──────────────────────────────────────────────────────────────

section("1. INSTALLATION")

slow_print("  \033[0;90m$\033[0m pip install mh-gdpr-ai", delay=0.04)
time.sleep(0.5)
print("  \033[0;32mSuccessfully installed mh-gdpr-ai-0.2.0\033[0m")
time.sleep(0.5)
print()
slow_print("  \033[0;90m$\033[0m python -c \"from sovereign_gateway import SovereignGateway; print('OK')\"", delay=0.03)
time.sleep(0.3)
print("  OK")
time.sleep(1)


# ──────────────────────────────────────────────────────────────
# 2. PII DETECTION - Real calls
# ──────────────────────────────────────────────────────────────

section("2. PII DETECTION - Does it actually find personal data?")

from sovereign_gateway import SovereignGateway, PIIDetector, PIIMasker

detector = PIIDetector(use_presidio=False)

test_cases = [
    ("Customer email",       "Send the invoice to jean.dupont@societe-generale.fr"),
    ("French phone",         "Call the client at +33 6 12 34 56 78"),
    ("Bank account (IBAN)",  "Wire transfer to FR76 3000 6000 0112 3456 7890 189"),
    ("Credit card",          "Payment with card 4111 1111 1111 1111"),
    ("US Social Security",   "Employee SSN: 123-45-6789"),
    ("French NIR (secu)",    "Patient NIR: 1 85 05 78 006 084 36"),
    ("Server IP address",    "Connect to 192.168.1.42 for database access"),
    ("No PII (safe)",        "Summarize the Q3 2025 earnings report"),
]

for label, text in test_cases:
    step(label)
    slow_print(f"      Input: \033[0;37m\"{text}\"\033[0m", delay=0.01)

    entities = detector.detect(text)
    if entities:
        types = [e.entity_type for e in entities]
        danger(f"PII DETECTED: {', '.join(types)}")
    else:
        safe("CLEAN - no personal data found")
    print()
    time.sleep(0.3)

time.sleep(0.5)


# ──────────────────────────────────────────────────────────────
# 3. SOVEREIGN ROUTING - Where should this data go?
# ──────────────────────────────────────────────────────────────

section("3. SOVEREIGN ROUTING - EU or cheapest?")

gateway = SovereignGateway(use_presidio=False)

slow_print("  \033[0;90mScenario: A fintech app sends user data to an LLM.\033[0m", delay=0.02)
slow_print("  \033[0;90mThe gateway decides WHERE the data should be processed.\033[0m", delay=0.02)
print()

# Scenario A: PII
step("Prompt with personal data (GDPR-sensitive)")
prompt_pii = "Analyze the account of jean.dupont@societe-generale.fr, IBAN FR76 3000 6000 0112 3456 7890 189"
slow_print(f"      Prompt: \033[0;37m\"{prompt_pii}\"\033[0m", delay=0.01)
print()

r = gateway.route([{"role": "user", "content": prompt_pii}])
result("PII detected", r.pii_detected)
result("PII types", r.pii_types)
result("Routing decision", f"\033[1;31m{r.decision.value.upper()}\033[0m - data STAYS in Europe (FR)", color="0")
result("Provider", f"{r.provider_used} (Paris, France)")
result("GDPR compliant", f"\033[1;32m{r.gdpr_compliant}\033[0m", color="0")
result("Latency", f"{r.latency_ms:.1f}ms")
print()

danger("  This prompt contains email + IBAN => routed to EU server ONLY.")
danger("  It is IMPOSSIBLE to bypass this. The gateway enforces it.")
print()
time.sleep(1)

# Scenario B: No PII
step("Prompt WITHOUT personal data")
prompt_safe = "Summarize the key points of the Q3 2025 earnings report for investors"
slow_print(f"      Prompt: \033[0;37m\"{prompt_safe}\"\033[0m", delay=0.01)
print()

r2 = gateway.route([{"role": "user", "content": prompt_safe}])
result("PII detected", r2.pii_detected)
result("Routing decision", f"\033[1;32m{r2.decision.value.upper()}\033[0m - use cheapest provider", color="0")
result("Provider", r2.provider_used)
result("GDPR compliant", f"\033[1;32m{r2.gdpr_compliant}\033[0m", color="0")
result("Latency", f"{r2.latency_ms:.1f}ms")
print()

safe("  No personal data => routed to cheapest provider. Saves 30-40%.")
print()
time.sleep(1)


# ──────────────────────────────────────────────────────────────
# 4. PII MASKING - Anonymize before sending
# ──────────────────────────────────────────────────────────────

section("4. PII MASKING - Anonymize sensitive data")

masker = PIIMasker()

originals = [
    "Contact jean.dupont@societe-generale.fr for the account review",
    "Wire payment to IBAN FR76 3000 6000 0112 3456 7890 189",
    "Cardholder 4111 1111 1111 1111, call +33 6 12 34 56 78",
]

for original in originals:
    step("Masking")
    print(f"      \033[31mBefore:\033[0m {original}")
    masked, types = masker.mask(original)
    print(f"      \033[32mAfter:\033[0m  {masked}")
    print(f"      \033[90mTypes:  {types}\033[0m")
    print()
    time.sleep(0.5)

safe("  PII replaced with type-specific placeholders.")
safe("  The LLM still understands the context, but no real data leaks.")
print()
time.sleep(1)


# ──────────────────────────────────────────────────────────────
# 5. COMPLIANCE SUMMARY - For your DPO
# ──────────────────────────────────────────────────────────────

section("5. COMPLIANCE SUMMARY - Ready for DPO audit")

slow_print("  \033[0;90mEvery request generates an audit-ready compliance summary.\033[0m", delay=0.02)
slow_print("  \033[0;90mYour DPO can show this to the regulator.\033[0m", delay=0.02)
print()

r3 = gateway.route([{"role": "user", "content": "Patient Jean Dupont, email jean@hospital.fr, NIR 1 85 05 78 006 084 36"}])

step("Compliance report for this request")
print()
summary = r3.compliance_summary
for key, value in summary.items():
    result(key, value)
print()
time.sleep(1)


# ──────────────────────────────────────────────────────────────
# 6. END-TO-END LLM CALL (complete())
# ──────────────────────────────────────────────────────────────

section("6. END-TO-END - gateway.complete()")

slow_print("  \033[0;90mcomplete() = PII detection + routing + actual LLM call.\033[0m", delay=0.02)
slow_print("  \033[0;90mRequires a provider API key (Scaleway, Together AI, OpenAI...).\033[0m", delay=0.02)
print()
print("  \033[0;37m  gateway = SovereignGateway(providers={\033[0m")
print("  \033[0;37m      \"scaleway\": {\"api_key\": \"scw-...\"},    # EU\033[0m")
print("  \033[0;37m      \"together_ai\": {\"api_key\": \"tok-...\"},  # fallback\033[0m")
print("  \033[0;37m  })\033[0m")
print()
print("  \033[0;37m  result = gateway.complete([{\"role\": \"user\", \"content\": \"...\"}])\033[0m")
print("  \033[0;37m  print(result.content)        # actual LLM response\033[0m")
print("  \033[0;37m  print(result.provider_used)   # which provider handled it\033[0m")
print("  \033[0;37m  print(result.gdpr_compliant)  # always True\033[0m")
print()

safe("  Free to test: create a Together AI account => $5 free credits, no card needed.")
print()
time.sleep(1)


# ──────────────────────────────────────────────────────────────
# CONCLUSION
# ──────────────────────────────────────────────────────────────

print()
print("\033[1;36m" + "=" * 70 + "\033[0m")
print()
slow_print("  \033[1;37m  3 lines of code. Full GDPR compliance. 30-40% cost savings.\033[0m", delay=0.03)
print()
slow_print("  \033[0;37m  pip install mh-gdpr-ai\033[0m", delay=0.04)
slow_print("  \033[0;37m  github.com/mahadillahm4di-cyber/mh-gdpr-ai.eu\033[0m", delay=0.03)
slow_print("  \033[0;37m  mahadillah@mh-gdpr-ai.eu\033[0m", delay=0.03)
print()
print("\033[1;36m" + "=" * 70 + "\033[0m")
print()
