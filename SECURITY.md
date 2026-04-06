# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do NOT open a public issue.**

Instead, send an email to: **mahadillah@mh-gdpr-ai.eu**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge your report within 48 hours and work on a fix.

## Scope

This project handles PII detection and routing decisions. Security concerns include:

- PII leaking into logs (we log types only, never content)
- PII bypass (false negatives in detection)
- Routing bypass (PII detected but not routed to EU)
- Dependency vulnerabilities

## Design Principles

- PII content is **never logged** — only types and counts
- EU routing **cannot be bypassed** when PII is detected
- Dual-layer detection (Presidio + regex) provides defense in depth
- All inputs validated through Pydantic models
