# Contributing to mh-gdpr-ai.eu

Thank you for your interest in contributing! This project aims to make GDPR compliance accessible to every team using LLMs.

## Getting Started

```bash
# Clone the repo
git clone https://github.com/mahadillahm4di-cyber/mh-gdpr-ai.eu.git
cd mh-gdpr-ai.eu

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .
```

## How to Contribute

### Reporting Bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

### Adding PII Patterns

We welcome new PII detection patterns, especially for non-US/non-EU formats. To add a new pattern:

1. Add the regex to `sovereign_gateway/pii/detector.py`
2. Add corresponding mask to `sovereign_gateway/pii/masker.py`
3. Add tests in `tests/test_pii_detector.py` and `tests/test_masker.py`
4. Include at least 3 test cases (basic, edge case, embedded in text)

### Adding Provider Support

To add a new EU provider:

1. Add the provider to the `Provider` enum in `models/schemas.py`
2. If EU-based, add to `EU_PROVIDERS`
3. Update the routing priority in `router/sovereign.py`
4. Add tests

### Pull Requests

1. Fork the repo and create a branch from `master`
2. Write tests for your changes
3. Ensure all tests pass: `pytest`
4. Ensure linting passes: `ruff check .`
5. Submit a PR with a clear description

## Code Standards

- Type hints on all public functions
- Docstrings (Google style) on all public classes and methods
- No secrets, API keys, or PII in code or tests
- Tests required for all new features

## Security

If you discover a security vulnerability, please report it privately. See [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
