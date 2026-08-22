"""Weather router — GET /api/weather/current & /forecast"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.models.schemas import WeatherForecastPoint, WeatherObservation
from app.simulation.engine import simulate_weather

router = APIRouter()


@router.get("/current", response_model=WeatherObservation)
async def get_weather_current(location: str = "Kutch, Gujarat"):
    return simulate_weather(location=location)


@router.get("/forecast", response_model=list[WeatherForecastPoint])
async def get_weather_forecast(hours: int = 24, location: str = "Kutch, Gujarat"):
    """Return an hourly weather forecast for the next `hours` hours."""
    now = datetime.now(timezone.utc)
    points = []
    for h in range(1, min(hours, 48) + 1):
        ts = now + timedelta(hours=h)
        obs = simulate_weather(ts=ts, location=location)
        points.append(
            WeatherForecastPoint(
                timestamp=ts,
                temperature_c=obs.temperature_c,
                wind_speed_ms=obs.wind_speed_ms,
                solar_irradiance_w_m2=obs.solar_irradiance_w_m2,
                cloud_cover_percent=obs.cloud_cover_percent,
                confidence=0.85,
            )
        )
    return points
