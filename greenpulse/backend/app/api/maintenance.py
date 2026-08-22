"""Maintenance router — GET /api/maintenance/risks"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import AssetHealth
from app.agents.predictive_maintenance import get_asset_health, get_maintenance_risks

router = APIRouter()


@router.get("/risks", response_model=list[AssetHealth])
async def get_all_risks():
    return get_maintenance_risks()


@router.get("/risks/{asset_id}", response_model=AssetHealth)
async def get_risk_for_asset(asset_id: str):
    health = get_asset_health(asset_id)
    if health is None:
        raise HTTPException(status_code=404, detail=f"No health data for '{asset_id}'")
    return health
