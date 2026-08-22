"""Grid router — delegates to Grid Integration Optimization Agent."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import GridStatus
from app.simulation.engine import simulate_grid_status
from app.agents.grid_optimization import get_grid_recommendation

router = APIRouter()


@router.get("/status", response_model=GridStatus)
async def get_grid_status():
    return simulate_grid_status()


@router.get("/recommendation")
async def get_grid_recommendation_endpoint():
    return get_grid_recommendation()
