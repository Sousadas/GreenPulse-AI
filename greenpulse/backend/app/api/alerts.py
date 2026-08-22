"""Alerts router — GET /api/alerts"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from app.models.schemas import Alert, AlertSeverity
from app.services.alert_service import generate_alerts

router = APIRouter()


@router.get("", response_model=list[Alert])
async def get_alerts(severity: Optional[AlertSeverity] = None):
    alerts = generate_alerts()
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    return alerts


@router.get("/{asset_id}", response_model=list[Alert])
async def get_asset_alerts(asset_id: str):
    return [a for a in generate_alerts() if a.asset_id == asset_id]
