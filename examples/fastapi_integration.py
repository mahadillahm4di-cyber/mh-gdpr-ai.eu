"""FastAPI integration example — mh-gdpr-ai.eu as middleware.

Shows how to add GDPR-compliant PII routing to any FastAPI application.
Run: uvicorn examples.fastapi_integration:app --reload

Requires: pip install mh-gdpr-ai[api]
"""

from fastapi import FastAPI
from pydantic import BaseModel

from sovereign_gateway import SovereignGateway

app = FastAPI(
    title="mh-gdpr-ai.eu",
    description="GDPR-compliant LLM routing with real-time PII detection",
    version="0.2.0",
)

# Configure with your provider API keys.
# PII detected -> routes to EU provider (Scaleway).
# No PII -> routes to cheapest provider.
gateway = SovereignGateway(
    providers={
        "scaleway": {"api_key": "scw-your-key"},  # EU (Paris)
        "together_ai": {"api_key": "tok-your-key"},  # Non-EU fallback
    },
)


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    model: str | None = None


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    pii_detected: bool
    pii_types: list[str]
    forced_eu: bool
    gdpr_compliant: bool
    latency_ms: float


class RouteResponse(BaseModel):
    routing_decision: str
    model: str
    provider: str
    pii_detected: bool
    pii_types: list[str]
    forced_eu: bool
    gdpr_compliant: bool
    latency_ms: float


@app.post("/v1/chat/complete", response_model=ChatResponse)
async def complete_chat(request: ChatRequest) -> ChatResponse:
    """End-to-end: PII detection + routing + LLM call.

    PII detected -> routed to EU provider (Scaleway/OVHcloud).
    No PII -> routed to cheapest provider.
    """
    result = gateway.complete(
        messages=request.messages,
        model=request.model,
    )

    return ChatResponse(
        content=result.content,
        model=result.model_used,
        provider=result.provider_used,
        pii_detected=result.pii_detected,
        pii_types=result.pii_types,
        forced_eu=result.forced_eu_routing,
        gdpr_compliant=result.gdpr_compliant,
        latency_ms=result.latency_ms,
    )


@app.post("/v1/chat/route", response_model=RouteResponse)
async def route_chat(request: ChatRequest) -> RouteResponse:
    """Decision only: PII detection + routing (no LLM call).

    Use this to check where a request would be routed.
    """
    result = gateway.route(
        messages=request.messages,
        model=request.model,
    )

    return RouteResponse(
        routing_decision=result.decision.value,
        model=result.model_used,
        provider=result.provider_used,
        pii_detected=result.pii_detected,
        pii_types=result.pii_types,
        forced_eu=result.forced_eu_routing,
        gdpr_compliant=result.gdpr_compliant,
        latency_ms=result.latency_ms,
    )


@app.post("/v1/pii/detect")
async def detect_pii(text: str) -> dict:
    """Detect PII in text and return the types found."""
    types = gateway.detect_pii(text)
    return {
        "has_pii": len(types) > 0,
        "pii_types": types,
    }


@app.post("/v1/pii/mask")
async def mask_pii(text: str) -> dict:
    """Mask PII in text with safe placeholders."""
    masked = gateway.mask(text)
    return {"masked_text": masked}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "mh-gdpr-ai.eu", "version": "0.2.0"}
