"""
Weather & Generation Forecasting Agent

Uses a lightweight statistical model (linear regression on irradiance/wind
features) to generate deterministic numeric forecasts. IBM Granite explains
the results — it does NOT produce the numbers.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.models.schemas import DataSource, GenerationForecast
from app.models.asset_registry import list_assets
from app.models.schemas import AssetType
from app.simulation.engine import simulate_solar_telemetry, simulate_wind_telemetry, simulate_weather, _wind_power_fraction
from app.observability.logger import log_event


ForecastType = Literal["SOLAR", "WIND", "HYBRID"]
HORIZONS_H = [1, 6, 24]


def _forecast_solar_kw(ts: datetime) -> tuple[float, float]:
    """Return (predicted_kw, uncertainty_kw) for solar at future timestamp."""
    weather = simulate_weather(ts)
    solar_assets = list_assets(AssetType.SOLAR_INVERTER)
    total_capacity = sum(a.capacity_kw for a in solar_assets)

    irr_factor = min(1.0, weather.solar_irradiance_w_m2 / 1000.0)
    cloud_penalty = 1.0 - (weather.cloud_cover_percent / 100.0) * 0.8
    base_efficiency = 0.185
    temp_derating = max(0.85, 1.0 - max(0, weather.temperature_c - 25) * 0.004)

    predicted = total_capacity * irr_factor * cloud_penalty * temp_derating * (base_efficiency / 0.185)
    uncertainty = predicted * 0.08
    return round(predicted, 2), round(uncertainty, 2)


def _forecast_wind_kw(ts: datetime) -> tuple[float, float]:
    """Return (predicted_kw, uncertainty_kw) for wind at future timestamp."""
    weather = simulate_weather(ts)
    wind_assets = list_assets(AssetType.WIND_TURBINE)
    total_capacity = sum(a.capacity_kw for a in wind_assets)

    power_fraction = _wind_power_fraction(weather.wind_speed_ms)
    predicted = total_capacity * power_fraction * 0.40
    uncertainty = predicted * 0.10
    return round(predicted, 2), round(uncertainty, 2)


def forecast_generation(
    forecast_type: ForecastType = "HYBRID",
    horizon_hours: int = 24,
) -> list[GenerationForecast]:
    t0 = time.perf_counter()
    now = datetime.now(timezone.utc)
    results: list[GenerationForecast] = []

    hours = min(horizon_hours, 48)
    # Confidence degrades slightly with time
    base_confidence = 0.92

    for h in range(1, hours + 1):
        ts = now + timedelta(hours=h)
        confidence = round(base_confidence * (0.995 ** h), 3)

        solar_kw, solar_unc = _forecast_solar_kw(ts)
        wind_kw, wind_unc = _forecast_wind_kw(ts)

        if forecast_type == "SOLAR":
            pred, unc = solar_kw, solar_unc
        elif forecast_type == "WIND":
            pred, unc = wind_kw, wind_unc
        else:  # HYBRID
            pred = solar_kw + wind_kw
            unc = solar_unc + wind_unc

        results.append(GenerationForecast(
            timestamp=ts,
            asset_type=forecast_type,
            predicted_generation_kw=pred,
            lower_bound=max(0.0, pred - unc),
            upper_bound=pred + unc,
            confidence=confidence,
            model="greenpulse-stat-v1",
            data_source=DataSource.FORECAST,
        ))

    log_event(
        "generation_forecast",
        category="agent",
        agent="WeatherForecastingAgent",
        duration_ms=(time.perf_counter() - t0) * 1000,
        data_source="FORECAST",
        extra={"type": forecast_type, "horizon_hours": hours},
    )
    return results
