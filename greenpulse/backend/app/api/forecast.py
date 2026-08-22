"""Forecast router — delegates to the Forecasting Agent."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter

from app.agents.forecasting import forecast_generation
from app.models.schemas import GenerationForecast

router = APIRouter()


@router.get("", response_model=list[GenerationForecast])
async def get_forecast(
    hours: int = 24,
    type: Literal["SOLAR", "WIND", "HYBRID"] = "HYBRID",
):
    return forecast_generation(type, hours)
