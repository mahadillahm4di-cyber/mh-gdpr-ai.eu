"""FastAPI integration example — mh-gdpr-ai.eu as a middleware.

Shows how to add GDPR-compliant PII routing to any FastAPI application.
Run: uvicorn examples.fastapi_integration:app --reload

Requires: pip install fastapi uvicorn
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sovereign_gateway import SovereignGateway

app = FastAPI(
    title="mh-gdpr-ai.eu",
    description="GDPR-compliant LLM routing with real-time PII detection",
    version="0.1.0",
)

gateway = SovereignGateway()


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    model: str | None = None


class ChatResponse(BaseModel):
    routing_decision: str
    model: str
    provider: str
    pii_detected: bool
    pii_types: list[str]
    forced_eu: bool
    gdpr_compliant: bool
    latency_ms: float


@app.post("/v1/chat/route", response_model=ChatResponse)
async def route_chat(request: ChatRequest) -> ChatResponse:
    """Analyze a chat request and return the routing decision.

    The gateway detects PII in the messages and routes to EU providers
    when personal data is found. No PII = cheapest provider.
    """
    result = gateway.route(
        messages=request.messages,
        model=request.model,
    )

    return ChatResponse(
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
    return {"status": "ok", "service": "mh-gdpr-ai.eu"}
