# mh-gdpr-ai.eu — production-ready container
# Multi-stage build for minimal attack surface

# --- Stage 1: Build ---
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY sovereign_gateway/ sovereign_gateway/

RUN pip install --no-cache-dir --prefix=/install .

# --- Stage 2: Production ---
FROM python:3.12-slim AS production

LABEL org.opencontainers.image.title="mh-gdpr-ai.eu"
LABEL org.opencontainers.image.description="GDPR-compliant LLM routing with PII detection"
LABEL org.opencontainers.image.source="https://github.com/mh-gdpr-ai/mh-gdpr-ai.eu"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# Non-root user
RUN groupadd -r gateway && useradd -r -g gateway -d /app -s /sbin/nologin gateway
WORKDIR /app

COPY --from=builder /install /usr/local
COPY sovereign_gateway/ sovereign_gateway/
COPY examples/ examples/

RUN chown -R gateway:gateway /app
USER gateway

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "from sovereign_gateway import SovereignGateway; print('ok')" || exit 1

ENTRYPOINT ["python", "-m", "sovereign_gateway"]
