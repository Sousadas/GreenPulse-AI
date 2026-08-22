"""Solar router — GET /api/solar/generation"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.asset_registry import list_assets
from app.models.schemas import AssetType, SolarTelemetry
from app.simulation.engine import simulate_solar_telemetry

router = APIRouter()


@router.get("/generation", response_model=list[SolarTelemetry])
async def get_solar_generation():
    ts = datetime.now(timezone.utc)
    assets = list_assets(AssetType.SOLAR_INVERTER) + [a for a in list_assets(AssetType.SOLAR_PANEL)]
    return [simulate_solar_telemetry(a.asset_id, a.capacity_kw, ts) for a in assets]
