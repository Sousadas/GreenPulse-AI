"""ibm_client.py — thin compatibility shim.

The real implementation has moved to app/services/watsonx_service.py.
This module re-exports the public symbols that the rest of the codebase
(orchestrator, api/system) already imports, so nothing else needs to change.
"""
from __future__ import annotations

from typing import Any

from app.services.watsonx_service import (
    generate_ai_response,
    probe_ibm_connectivity,
    reset_ibm_client,
    _get_ibm_client as get_granite_client,
)
from app.core.config import get_settings


# ---------------------------------------------------------------------------
# granite_generate — async wrapper kept for backward-compat with orchestrator
# ---------------------------------------------------------------------------

async def granite_generate(prompt: str) -> str:
    """Async generate — delegates to watsonx_service.generate_ai_response().

    Returns the answer string only (orchestrator builds the full response dict).
    """
    response = await generate_ai_response(prompt)
    return response.answer


# ---------------------------------------------------------------------------
# probe_granite — kept for backward-compat with api/system.py
# ---------------------------------------------------------------------------

async def probe_granite() -> dict[str, Any]:
    """Alias for probe_ibm_connectivity() — used by existing system router."""
    result = await probe_ibm_connectivity()
    # Map new keys to existing shape expected by system.py
    settings = get_settings()
    return {
        "status": result.get("status", "UNKNOWN"),
        "model": result.get("model", settings.granite_model_id),
        "region": result.get("region", settings.ibm_region),
        "message": result.get("message", ""),
        "available": result.get("available", False),
        "mode": result.get("mode", settings.ai_mode),
        "effective_mode": result.get("effective_mode", settings.effective_ai_mode),
    }


__all__ = [
    "granite_generate",
    "probe_granite",
    "get_granite_client",
    "reset_ibm_client",
    "generate_ai_response",
    "probe_ibm_connectivity",
]
