"""Wind router — GET /api/wind/generation"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.asset_registry import list_assets
from app.models.schemas import AssetType, WindTelemetry
from app.simulation.engine import simulate_wind_telemetry

router = APIRouter()


@router.get("/generation", response_model=list[WindTelemetry])
async def get_wind_generation():
    ts = datetime.now(timezone.utc)
    assets = list_assets(AssetType.WIND_TURBINE)
    return [simulate_wind_telemetry(a.asset_id, a.capacity_kw, ts) for a in assets]
