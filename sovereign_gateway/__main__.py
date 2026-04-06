"""Entry point for running mh-gdpr-ai.eu as a module.

Usage: python -m sovereign_gateway
"""

from sovereign_gateway import SovereignGateway


def main() -> None:
    gateway = SovereignGateway(use_presidio=False)

    print()
    print("  mh-gdpr-ai.eu v0.1.0")
    print("  GDPR-compliant LLM routing with PII detection")
    print()
    print("  Try it:")
    print('    from sovereign_gateway import SovereignGateway')
    print('    gw = SovereignGateway()')
    print('    result = gw.route([{"role": "user", "content": "test@email.com"}])')
    print()

    # Quick self-test
    result = gateway.route([
        {"role": "user", "content": "Hello, my email is jean@company.fr"},
    ])
    print(f"  Self-test: PII detected={result.pii_detected}, EU forced={result.forced_eu_routing}")
    print("  Status: OK")
    print()


if __name__ == "__main__":
    main()
