"""Simulation control router — POST /api/simulation/fault"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.simulation.engine import SimulationScenario, get_scenario, set_scenario

router = APIRouter()


class ScenarioRequest(BaseModel):
    scenario: SimulationScenario
    intensity: float = 1.0


@router.post("/fault")
async def set_simulation_scenario(req: ScenarioRequest):
    set_scenario(req.scenario, req.intensity)
    return {
        "active_scenario": req.scenario,
        "intensity": req.intensity,
        "message": f"Simulation scenario '{req.scenario}' activated at intensity {req.intensity}.",
    }


@router.get("/status")
async def get_simulation_status():
    return {
        "active_scenario": get_scenario(),
        "available_scenarios": [s.value for s in SimulationScenario],
    }
