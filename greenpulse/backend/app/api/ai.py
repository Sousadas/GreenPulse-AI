"""AI router — POST /api/ai/query, GET /api/health/ai, POST /api/ai/test"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.orchestrator import orchestrate
from app.services.watsonx_service import generate_ai_response, probe_ibm_connectivity
from app.core.config import get_settings

router = APIRouter()


class AIQuery(BaseModel):
    question: str
    context: dict = {}


class TestPrompt(BaseModel):
    prompt: str = "Briefly explain the current renewable energy situation at the GreenPulse plant."


# ---------------------------------------------------------------------------
# Main AI assistant endpoint
# ---------------------------------------------------------------------------

@router.post("/query")
async def ai_query(query: AIQuery):
    """Route a natural-language question through the GreenPulse Orchestrator.

    All numerical context is gathered from live simulation/asset data before
    the prompt is sent to IBM Granite. Granite explains — it does not invent numbers.
    """
    return await orchestrate(query.question)


# ---------------------------------------------------------------------------
# Health check — GET /api/health/ai
# ---------------------------------------------------------------------------

@router.get("/health")
async def ai_health():
    """Return IBM Granite connectivity status.

    Never returns the API key or IAM tokens.
    """
    settings = get_settings()
    probe = await probe_ibm_connectivity()
    return {
        "provider": "IBM watsonx.ai",
        "model": settings.granite_model_id,
        "url": settings.watsonx_url,
        "region": settings.ibm_region,
        "configured": settings.granite_configured,
        "available": probe.get("available", False),
        "mode": settings.ai_mode,
        "effective_mode": settings.effective_ai_mode,
        "status": probe.get("status"),
        "message": probe.get("message"),
        "project_id_prefix": probe.get("project_id_prefix", ""),
    }


# ---------------------------------------------------------------------------
# Test endpoint — POST /api/ai/test (dev only)
# ---------------------------------------------------------------------------

@router.post("/test")
async def ai_test(body: TestPrompt):
    """Send a single prompt to IBM Granite and return the raw response.

    Development / connectivity-check endpoint.
    Never returns the API key.
    """
    settings = get_settings()
    response = await generate_ai_response(body.prompt)
    return {
        "provider": "IBM watsonx.ai",
        "model": settings.granite_model_id,
        "effective_mode": settings.effective_ai_mode,
        "prompt_length": len(body.prompt),
        "response": response.answer,
        "success": response.success,
        "duration_ms": response.duration_ms,
        "error": response.error,
    }
