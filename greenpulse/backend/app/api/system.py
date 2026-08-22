"""System router — /api/system/info, /api/system/granite"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.services.watsonx_service import probe_ibm_connectivity
from app.simulation.engine import get_scenario

router = APIRouter()


@router.get("/granite")
async def granite_status():
    """IBM Granite connectivity and configuration status. Never returns secrets."""
    return await probe_ibm_connectivity()


@router.get("/info")
async def system_info():
    """Full system info including AI mode, data mode, and simulation state."""
    settings = get_settings()
    return {
        "service": "GreenPulse AI",
        "version": "0.2.0",
        "env": settings.app_env,
        "data_source_mode": settings.data_source_mode,
        "granite_configured": settings.granite_configured,
        "granite_model": settings.granite_model_id,
        "region": settings.ibm_region,
        "url": settings.watsonx_url,
        "ai_mode": settings.ai_mode,
        "effective_ai_mode": settings.effective_ai_mode,
        "active_simulation": get_scenario().value,
    }
