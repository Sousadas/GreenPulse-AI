"""Synthetic data simulation engine.

Generates realistic renewable-energy telemetry following physical laws:
  - Solar generation follows a bell-curve correlated with irradiance and sun angle
  - Wind follows turbine power curve (cut-in / rated / cut-out speeds)
  - Fault injection simulates realistic degradation patterns
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.models.schemas import (
    AssetStatus,
    DataSource,
    GridStatus,
    SolarTelemetry,
    WeatherObservation,
    WindTelemetry,
)


# ---------------------------------------------------------------------------
# Fault injection modes
# ---------------------------------------------------------------------------

class SimulationScenario(str, Enum):
    NORMAL = "NORMAL"
    SOLAR_INVERTER_DEGRADATION = "SOLAR_INVERTER_DEGRADATION"   # SOL-INV-042
    WIND_TURBINE_OVERHEATING = "WIND_TURBINE_OVERHEATING"       # WT-017
    HIGH_WIND_EVENT = "HIGH_WIND_EVENT"
    CLOUD_COVER_EVENT = "CLOUD_COVER_EVENT"
    RENEWABLE_SURPLUS = "RENEWABLE_SURPLUS"
    GRID_DEMAND_INCREASE = "GRID_DEMAND_INCREASE"


# Global mutable state (process-level; swapped via /api/simulation/fault)
_active_scenario: SimulationScenario = SimulationScenario.NORMAL
_scenario_intensity: float = 1.0  # 0.0 – 1.0


def set_scenario(scenario: SimulationScenario, intensity: float = 1.0) -> None:
    global _active_scenario, _scenario_intensity
    _active_scenario = scenario
    _scenario_intensity = max(0.0, min(1.0, intensity))


def get_scenario() -> SimulationScenario:
    return _active_scenario


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _solar_angle_factor(ts: datetime) -> float:
    """Return a 0–1 factor representing approximate solar elevation for Gujarat."""
    # Gujarat: lat ~23°N  — civil sunrise ~06:00, sunset ~18:30 local (UTC+5:30)
    local_hour = (ts.hour + ts.minute / 60.0 + 5.5) % 24  # approximate IST
    if local_hour < 6.0 or local_hour > 18.5:
        return 0.0
    peak = 12.25  # solar noon approx
    spread = 6.5
    return max(0.0, math.cos(math.pi * (local_hour - peak) / spread) ** 2)


def _jitter(value: float, pct: float = 0.02) -> float:
    """Add ±pct Gaussian noise."""
    return value * (1.0 + random.gauss(0, pct))


# ---------------------------------------------------------------------------
# Weather simulation
# ---------------------------------------------------------------------------

def simulate_weather(ts: Optional[datetime] = None, location: str = "Kutch, Gujarat") -> WeatherObservation:
    ts = ts or datetime.now(timezone.utc)
    solar_factor = _solar_angle_factor(ts)

    cloud_cover = 10.0  # baseline clear
    if _active_scenario == SimulationScenario.CLOUD_COVER_EVENT:
        cloud_cover = 70.0 + _scenario_intensity * 20.0

    irradiance = _jitter(1000.0 * solar_factor * (1 - cloud_cover / 120))
    irradiance = max(0.0, irradiance)

    wind_speed = _jitter(7.5)
    if _active_scenario == SimulationScenario.HIGH_WIND_EVENT:
        wind_speed = _jitter(14.0 + _scenario_intensity * 8.0)

    return WeatherObservation(
        timestamp=ts,
        location=location,
        temperature_c=_jitter(32.0),
        humidity=_jitter(0.45),
        wind_speed_ms=wind_speed,
        wind_direction=_jitter(225.0, 0.05),
        solar_irradiance_w_m2=irradiance,
        cloud_cover_percent=cloud_cover,
        rainfall_mm=0.0,
        data_source=DataSource.SIMULATED,
    )


# ---------------------------------------------------------------------------
# Solar telemetry simulation
# ---------------------------------------------------------------------------

def simulate_solar_telemetry(
    asset_id: str,
    capacity_kw: float,
    ts: Optional[datetime] = None,
) -> SolarTelemetry:
    ts = ts or datetime.now(timezone.utc)
    weather = simulate_weather(ts)

    solar_factor = _solar_angle_factor(ts)
    base_efficiency = 0.185  # realistic monocrystalline panel efficiency
    inverter_temp = _jitter(45.0)

    # Apply scenario degradation to target inverter
    efficiency = base_efficiency
    fault_factor = 1.0
    if _active_scenario == SimulationScenario.SOLAR_INVERTER_DEGRADATION and asset_id == "SOL-INV-042":
        degradation = _scenario_intensity * 0.35
        efficiency *= (1 - degradation)
        inverter_temp = _jitter(72.0 + _scenario_intensity * 18.0)
        fault_factor = 1 - degradation

    irradiance = weather.solar_irradiance_w_m2
    panel_temp = weather.temperature_c + 25 * solar_factor
    voltage = _jitter(48.0 * fault_factor)
    current = _jitter(capacity_kw * 1000 / max(voltage, 1) * solar_factor * fault_factor)
    power_kw = _jitter(capacity_kw * solar_factor * efficiency / base_efficiency * fault_factor)
    power_kw = max(0.0, min(power_kw, capacity_kw))

    status = AssetStatus.ONLINE
    if _active_scenario == SimulationScenario.SOLAR_INVERTER_DEGRADATION and asset_id == "SOL-INV-042":
        if _scenario_intensity > 0.6:
            status = AssetStatus.FAULT
        elif _scenario_intensity > 0.3:
            status = AssetStatus.WARNING

    return SolarTelemetry(
        timestamp=ts,
        asset_id=asset_id,
        irradiance_w_m2=irradiance,
        ambient_temperature_c=weather.temperature_c,
        panel_temperature_c=panel_temp,
        voltage_v=voltage,
        current_a=current,
        power_kw=power_kw,
        efficiency=efficiency,
        inverter_temperature_c=inverter_temp,
        status=status,
        data_source=DataSource.SIMULATED,
    )


# ---------------------------------------------------------------------------
# Wind telemetry simulation  (turbine power curve)
# ---------------------------------------------------------------------------

def _wind_power_fraction(wind_speed_ms: float) -> float:
    """Simplified wind turbine power curve.

    Cut-in: 3 m/s, Rated: 12 m/s, Cut-out: 25 m/s
    """
    if wind_speed_ms < 3.0 or wind_speed_ms > 25.0:
        return 0.0
    if wind_speed_ms >= 12.0:
        return 1.0
    # Cubic between cut-in and rated
    return ((wind_speed_ms - 3.0) / (12.0 - 3.0)) ** 3


def simulate_wind_telemetry(
    asset_id: str,
    capacity_kw: float,
    ts: Optional[datetime] = None,
) -> WindTelemetry:
    ts = ts or datetime.now(timezone.utc)
    weather = simulate_weather(ts)
    wind_speed = weather.wind_speed_ms

    rpm_base = 15.0 + wind_speed * 1.2
    gen_temp = _jitter(55.0)
    vibration = _jitter(1.2)
    efficiency = 0.40  # Betz limit ~59 %, practical ~40 %

    fault_factor = 1.0
    if _active_scenario == SimulationScenario.WIND_TURBINE_OVERHEATING and asset_id == "WT-017":
        gen_temp = _jitter(85.0 + _scenario_intensity * 30.0)
        vibration = _jitter(3.5 + _scenario_intensity * 4.0)
        efficiency *= (1 - _scenario_intensity * 0.25)
        fault_factor = 1 - _scenario_intensity * 0.3

    power_fraction = _wind_power_fraction(wind_speed)
    power_kw = _jitter(capacity_kw * power_fraction * efficiency / 0.40 * fault_factor)
    power_kw = max(0.0, min(power_kw, capacity_kw))

    status = AssetStatus.ONLINE
    if _active_scenario == SimulationScenario.WIND_TURBINE_OVERHEATING and asset_id == "WT-017":
        if gen_temp > 110 or vibration > 6.0:
            status = AssetStatus.FAULT
        elif gen_temp > 85 or vibration > 3.5:
            status = AssetStatus.WARNING

    return WindTelemetry(
        timestamp=ts,
        asset_id=asset_id,
        wind_speed_ms=wind_speed,
        wind_direction=weather.wind_direction,
        turbine_rpm=_jitter(rpm_base),
        generator_temperature_c=gen_temp,
        vibration_mm_s=vibration,
        power_kw=power_kw,
        efficiency=efficiency,
        status=status,
        data_source=DataSource.SIMULATED,
    )


# ---------------------------------------------------------------------------
# Grid simulation
# ---------------------------------------------------------------------------

def simulate_grid_status(ts: Optional[datetime] = None) -> GridStatus:
    from app.models.asset_registry import list_assets
    from app.models.schemas import AssetType

    ts = ts or datetime.now(timezone.utc)

    # Sum generation across all solar inverters and wind turbines
    solar_assets = list_assets(AssetType.SOLAR_INVERTER) + list_assets(AssetType.SOLAR_PANEL)
    wind_assets = list_assets(AssetType.WIND_TURBINE)

    solar_gen_mw = sum(
        simulate_solar_telemetry(a.asset_id, a.capacity_kw, ts).power_kw
        for a in solar_assets
    ) / 1000.0

    wind_gen_mw = sum(
        simulate_wind_telemetry(a.asset_id, a.capacity_kw, ts).power_kw
        for a in wind_assets
    ) / 1000.0

    renewable_mw = solar_gen_mw + wind_gen_mw

    base_load = 18.0
    if _active_scenario == SimulationScenario.GRID_DEMAND_INCREASE:
        base_load += _scenario_intensity * 12.0

    grid_load = _jitter(base_load, 0.03)
    surplus = renewable_mw - grid_load
    export = max(0.0, surplus)
    imp = max(0.0, -surplus)

    return GridStatus(
        timestamp=ts,
        grid_voltage_v=_jitter(132000.0, 0.005),
        grid_frequency_hz=_jitter(50.0, 0.002),
        grid_load_mw=grid_load,
        grid_import_mw=imp,
        grid_export_mw=export,
        renewable_generation_mw=renewable_mw,
        renewable_surplus_mw=surplus,
        data_source=DataSource.SIMULATED,
    )
