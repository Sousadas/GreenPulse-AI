"""Assets router — full CRUD + performance, health, alerts per asset."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.asset_registry import get_asset, list_assets
from app.models.schemas import Asset, AssetHealth, AssetPerformance, AssetType, Alert
from app.agents.asset_performance import get_asset_performance
from app.agents.predictive_maintenance import get_asset_health
from app.services.alert_service import generate_alerts

router = APIRouter()


@router.get("", response_model=list[Asset])
async def get_assets(asset_type: AssetType | None = None):
    return list_assets(asset_type)


@router.get("/{asset_id}", response_model=Asset)
async def get_asset_by_id(asset_id: str):
    asset = get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")
    return asset


@router.get("/{asset_id}/performance", response_model=AssetPerformance)
async def get_asset_performance_endpoint(asset_id: str):
    if not get_asset(asset_id):
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")
    perf = get_asset_performance(asset_id)
    if perf is None:
        raise HTTPException(status_code=422, detail=f"Performance not available for asset type of '{asset_id}'")
    return perf


@router.get("/{asset_id}/health", response_model=AssetHealth)
async def get_asset_health_endpoint(asset_id: str):
    if not get_asset(asset_id):
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")
    health = get_asset_health(asset_id)
    if health is None:
        raise HTTPException(status_code=422, detail=f"Health score not available for asset type of '{asset_id}'")
    return health


@router.get("/{asset_id}/alerts", response_model=list[Alert])
async def get_asset_alerts_endpoint(asset_id: str):
    if not get_asset(asset_id):
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")
    return [a for a in generate_alerts() if a.asset_id == asset_id]
