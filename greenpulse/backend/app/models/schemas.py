"""Core Pydantic models — data structures for every domain entity."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DataSource(str, Enum):
    LIVE = "LIVE"
    API = "API"
    SIMULATED = "SIMULATED"
    HISTORICAL = "HISTORICAL"
    FORECAST = "FORECAST"


class AssetType(str, Enum):
    SOLAR_PANEL = "SOLAR_PANEL"
    SOLAR_INVERTER = "SOLAR_INVERTER"
    WIND_TURBINE = "WIND_TURBINE"
    GENERATOR = "GENERATOR"
    TRANSFORMER = "TRANSFORMER"
    GRID_INTERFACE = "GRID_INTERFACE"


class AssetStatus(str, Enum):
    ONLINE = "ONLINE"
    WARNING = "WARNING"
    FAULT = "FAULT"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MaintenanceRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

class Asset(BaseModel):
    asset_id: str
    asset_type: AssetType
    location: str
    capacity_kw: float
    manufacturer: str
    model: str
    installation_date: datetime
    status: AssetStatus
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

class SolarTelemetry(BaseModel):
    timestamp: datetime
    asset_id: str
    irradiance_w_m2: float
    ambient_temperature_c: float
    panel_temperature_c: float
    voltage_v: float
    current_a: float
    power_kw: float
    efficiency: float                    # 0.0 – 1.0
    inverter_temperature_c: float
    status: AssetStatus
    data_source: DataSource = DataSource.SIMULATED


class WindTelemetry(BaseModel):
    timestamp: datetime
    asset_id: str
    wind_speed_ms: float
    wind_direction: float                # degrees
    turbine_rpm: float
    generator_temperature_c: float
    vibration_mm_s: float
    power_kw: float
    efficiency: float
    status: AssetStatus
    data_source: DataSource = DataSource.SIMULATED


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

class WeatherObservation(BaseModel):
    timestamp: datetime
    location: str
    temperature_c: float
    humidity: float                      # 0.0 – 1.0
    wind_speed_ms: float
    wind_direction: float
    solar_irradiance_w_m2: float
    cloud_cover_percent: float           # 0–100
    rainfall_mm: float
    data_source: DataSource = DataSource.SIMULATED


class WeatherForecastPoint(BaseModel):
    timestamp: datetime
    temperature_c: float
    wind_speed_ms: float
    solar_irradiance_w_m2: float
    cloud_cover_percent: float
    confidence: float = 1.0
    data_source: DataSource = DataSource.FORECAST


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------

class GridStatus(BaseModel):
    timestamp: datetime
    grid_voltage_v: float
    grid_frequency_hz: float
    grid_load_mw: float
    grid_import_mw: float
    grid_export_mw: float
    renewable_generation_mw: float
    renewable_surplus_mw: float
    data_source: DataSource = DataSource.SIMULATED


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

class AssetPerformance(BaseModel):
    asset_id: str
    expected_power_kw: float
    actual_power_kw: float
    performance_ratio: float             # 0–100 %
    status: AssetStatus
    timestamp: datetime
    data_source: DataSource


# ---------------------------------------------------------------------------
# Health & Maintenance
# ---------------------------------------------------------------------------

class AssetHealth(BaseModel):
    asset_id: str
    health_score: float                  # 0–100
    maintenance_risk: MaintenanceRisk
    contributing_factors: list[str] = Field(default_factory=list)
    timestamp: datetime
    data_source: DataSource = DataSource.SIMULATED


class MaintenanceHistory(BaseModel):
    record_id: str
    asset_id: str
    timestamp: datetime
    maintenance_type: str
    description: str
    technician: str
    outcome: str


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class Alert(BaseModel):
    alert_id: str
    asset_id: str
    timestamp: datetime
    severity: AlertSeverity
    category: str
    description: str
    evidence: list[str] = Field(default_factory=list)
    recommendation: str
    status: str = "OPEN"                 # OPEN | ACKNOWLEDGED | RESOLVED


# ---------------------------------------------------------------------------
# Forecasts
# ---------------------------------------------------------------------------

class GenerationForecast(BaseModel):
    timestamp: datetime
    asset_type: str                      # SOLAR | WIND | HYBRID
    predicted_generation_kw: float
    lower_bound: float
    upper_bound: float
    confidence: float
    model: str
    data_source: DataSource = DataSource.FORECAST


# ---------------------------------------------------------------------------
# Agent events (observability)
# ---------------------------------------------------------------------------

class AgentEvent(BaseModel):
    event_id: str
    timestamp: datetime
    agent: str
    tool: Optional[str] = None
    asset_id: Optional[str] = None
    duration_ms: Optional[float] = None
    data_source: Optional[DataSource] = None
    model: Optional[str] = None
    summary: str
    extra: dict[str, Any] = Field(default_factory=dict)
