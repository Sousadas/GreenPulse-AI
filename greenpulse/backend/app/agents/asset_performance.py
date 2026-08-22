"""
Asset Performance Monitoring Agent

Calculates performance ratio, detects anomalies, and classifies asset status
using deterministic numerical methods before passing results to Granite for
explanation generation.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.models.schemas import (
    Alert, AlertSeverity, AssetPerformance, AssetStatus,
    AssetType, DataSource, SolarTelemetry, WindTelemetry,
)
from app.models.asset_registry import get_asset, list_assets
from app.simulation.engine import simulate_solar_telemetry, simulate_wind_telemetry
from app.observability.logger import log_event


# ---------------------------------------------------------------------------
# Thresholds (configurable — move to Settings in production)
# ---------------------------------------------------------------------------

SOLAR_INVERTER_TEMP_WARN = 65.0       # °C
SOLAR_INVERTER_TEMP_CRIT = 80.0
SOLAR_MIN_EFFICIENCY = 0.14           # below this = degraded
SOLAR_PERF_WARN_PCT = 80.0            # performance ratio %
SOLAR_PERF_CRIT_PCT = 60.0

WIND_GEN_TEMP_WARN = 80.0             # °C
WIND_GEN_TEMP_CRIT = 105.0
WIND_VIBRATION_WARN = 3.5             # mm/s
WIND_VIBRATION_CRIT = 6.0
WIND_PERF_WARN_PCT = 70.0
WIND_PERF_CRIT_PCT = 50.0


# ---------------------------------------------------------------------------
# Performance ratio calculation (§6 of spec)
# ---------------------------------------------------------------------------

def calculate_performance_ratio(actual_kw: float, capacity_kw: float, solar_factor: float = 1.0) -> float:
    """Return performance ratio 0–100. Uses solar_factor for expected output."""
    expected = capacity_kw * solar_factor
    if expected <= 0:
        return 100.0
    return round((actual_kw / expected) * 100, 2)


# ---------------------------------------------------------------------------
# Per-asset anomaly detection (numerical layer)
# ---------------------------------------------------------------------------

def _classify_solar(telem: SolarTelemetry, capacity_kw: float) -> tuple[AssetStatus, list[str]]:
    """Return (status, list-of-anomaly-descriptions)."""
    anomalies: list[str] = []
    worst = AssetStatus.ONLINE

    # Temperature
    if telem.inverter_temperature_c >= SOLAR_INVERTER_TEMP_CRIT:
        anomalies.append(f"Critical inverter temperature: {telem.inverter_temperature_c:.1f}°C (threshold {SOLAR_INVERTER_TEMP_CRIT}°C)")
        worst = AssetStatus.FAULT
    elif telem.inverter_temperature_c >= SOLAR_INVERTER_TEMP_WARN:
        anomalies.append(f"High inverter temperature: {telem.inverter_temperature_c:.1f}°C (threshold {SOLAR_INVERTER_TEMP_WARN}°C)")
        if worst == AssetStatus.ONLINE:
            worst = AssetStatus.WARNING

    # Efficiency
    if telem.efficiency < SOLAR_MIN_EFFICIENCY:
        anomalies.append(f"Low efficiency: {telem.efficiency:.3f} (baseline 0.185)")
        if worst == AssetStatus.ONLINE:
            worst = AssetStatus.WARNING

    # Performance ratio (only meaningful when irradiance is present)
    if telem.irradiance_w_m2 > 50:
        solar_factor = min(1.0, telem.irradiance_w_m2 / 1000.0)
        pr = calculate_performance_ratio(telem.power_kw, capacity_kw, solar_factor)
        if pr < SOLAR_PERF_CRIT_PCT:
            anomalies.append(f"Critical performance ratio: {pr:.1f}% (threshold {SOLAR_PERF_CRIT_PCT}%)")
            worst = AssetStatus.FAULT
        elif pr < SOLAR_PERF_WARN_PCT:
            anomalies.append(f"Low performance ratio: {pr:.1f}% (threshold {SOLAR_PERF_WARN_PCT}%)")
            if worst == AssetStatus.ONLINE:
                worst = AssetStatus.WARNING

    return worst, anomalies


def _classify_wind(telem: WindTelemetry, capacity_kw: float) -> tuple[AssetStatus, list[str]]:
    anomalies: list[str] = []
    worst = AssetStatus.ONLINE

    if telem.generator_temperature_c >= WIND_GEN_TEMP_CRIT:
        anomalies.append(f"Critical generator temperature: {telem.generator_temperature_c:.1f}°C (threshold {WIND_GEN_TEMP_CRIT}°C)")
        worst = AssetStatus.FAULT
    elif telem.generator_temperature_c >= WIND_GEN_TEMP_WARN:
        anomalies.append(f"High generator temperature: {telem.generator_temperature_c:.1f}°C (threshold {WIND_GEN_TEMP_WARN}°C)")
        if worst == AssetStatus.ONLINE:
            worst = AssetStatus.WARNING

    if telem.vibration_mm_s >= WIND_VIBRATION_CRIT:
        anomalies.append(f"Critical vibration: {telem.vibration_mm_s:.2f} mm/s (threshold {WIND_VIBRATION_CRIT} mm/s)")
        worst = AssetStatus.FAULT
    elif telem.vibration_mm_s >= WIND_VIBRATION_WARN:
        anomalies.append(f"Elevated vibration: {telem.vibration_mm_s:.2f} mm/s (threshold {WIND_VIBRATION_WARN} mm/s)")
        if worst == AssetStatus.ONLINE:
            worst = AssetStatus.WARNING

    if telem.wind_speed_ms > 3.0:
        pr = calculate_performance_ratio(telem.power_kw, capacity_kw)
        if pr < WIND_PERF_CRIT_PCT:
            anomalies.append(f"Critical performance ratio: {pr:.1f}% (threshold {WIND_PERF_CRIT_PCT}%)")
            worst = AssetStatus.FAULT
        elif pr < WIND_PERF_WARN_PCT:
            anomalies.append(f"Low performance ratio: {pr:.1f}% (threshold {WIND_PERF_WARN_PCT}%)")
            if worst == AssetStatus.ONLINE:
                worst = AssetStatus.WARNING

    return worst, anomalies


# ---------------------------------------------------------------------------
# Public agent functions
# ---------------------------------------------------------------------------

def get_asset_performance(asset_id: str) -> AssetPerformance | None:
    """Return computed AssetPerformance for a single asset."""
    asset = get_asset(asset_id)
    if not asset:
        return None

    ts = datetime.now(timezone.utc)

    if asset.asset_type in (AssetType.SOLAR_INVERTER, AssetType.SOLAR_PANEL):
        telem = simulate_solar_telemetry(asset_id, asset.capacity_kw, ts)
        solar_factor = min(1.0, max(0.0, telem.irradiance_w_m2 / 1000.0))
        pr = calculate_performance_ratio(telem.power_kw, asset.capacity_kw, solar_factor)
        status, _ = _classify_solar(telem, asset.capacity_kw)
        return AssetPerformance(
            asset_id=asset_id,
            expected_power_kw=round(asset.capacity_kw * solar_factor, 2),
            actual_power_kw=round(telem.power_kw, 2),
            performance_ratio=pr,
            status=status,
            timestamp=ts,
            data_source=DataSource.SIMULATED,
        )

    if asset.asset_type == AssetType.WIND_TURBINE:
        telem = simulate_wind_telemetry(asset_id, asset.capacity_kw, ts)
        from app.simulation.engine import _wind_power_fraction
        expected_kw = asset.capacity_kw * _wind_power_fraction(telem.wind_speed_ms)
        pr = calculate_performance_ratio(telem.power_kw, asset.capacity_kw)
        status, _ = _classify_wind(telem, asset.capacity_kw)
        return AssetPerformance(
            asset_id=asset_id,
            expected_power_kw=round(expected_kw, 2),
            actual_power_kw=round(telem.power_kw, 2),
            performance_ratio=pr,
            status=status,
            timestamp=ts,
            data_source=DataSource.SIMULATED,
        )

    return None


def get_all_asset_anomalies() -> list[dict[str, Any]]:
    """Scan all solar/wind assets and return anomaly records."""
    t0 = time.perf_counter()
    ts = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []

    for asset in list_assets():
        if asset.asset_type in (AssetType.SOLAR_INVERTER, AssetType.SOLAR_PANEL):
            telem = simulate_solar_telemetry(asset.asset_id, asset.capacity_kw, ts)
            status, anomalies = _classify_solar(telem, asset.capacity_kw)
            if anomalies:
                results.append({
                    "asset_id": asset.asset_id,
                    "asset_type": asset.asset_type,
                    "status": status,
                    "anomalies": anomalies,
                    "power_kw": telem.power_kw,
                    "timestamp": ts,
                })

        elif asset.asset_type == AssetType.WIND_TURBINE:
            telem = simulate_wind_telemetry(asset.asset_id, asset.capacity_kw, ts)
            status, anomalies = _classify_wind(telem, asset.capacity_kw)
            if anomalies:
                results.append({
                    "asset_id": asset.asset_id,
                    "asset_type": asset.asset_type,
                    "status": status,
                    "anomalies": anomalies,
                    "power_kw": telem.power_kw,
                    "timestamp": ts,
                })

    log_event(
        "asset_anomaly_scan",
        category="agent",
        agent="AssetPerformanceAgent",
        duration_ms=(time.perf_counter() - t0) * 1000,
        data_source="SIMULATED",
        extra={"anomalies_found": len(results)},
    )
    return results
