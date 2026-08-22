"""
Predictive Maintenance Agent

Computes Asset Health Score (0–100) and Maintenance Risk (LOW/MEDIUM/HIGH/CRITICAL)
from multi-signal telemetry trends. Uses rule-based scoring on numerical signals —
Granite explains the result, does not compute it.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from app.models.schemas import (
    AssetHealth, AssetType, DataSource, MaintenanceRisk,
)
from app.models.asset_registry import get_asset, list_assets
from app.simulation.engine import simulate_solar_telemetry, simulate_wind_telemetry
from app.observability.logger import log_event


# ---------------------------------------------------------------------------
# Scoring weights (each dimension scored 0–100, then weighted)
# ---------------------------------------------------------------------------

def _solar_health_score(asset_id: str, capacity_kw: float) -> tuple[float, MaintenanceRisk, list[str]]:
    ts = datetime.now(timezone.utc)
    telem = simulate_solar_telemetry(asset_id, capacity_kw, ts)
    factors: list[str] = []
    score = 100.0

    # Inverter temperature contribution (max deduction: 40 pts)
    if telem.inverter_temperature_c >= 80:
        deduct = 40.0
        factors.append(f"Critical inverter temperature ({telem.inverter_temperature_c:.1f}°C)")
    elif telem.inverter_temperature_c >= 65:
        deduct = 20.0 + (telem.inverter_temperature_c - 65) / 15 * 20
        factors.append(f"Elevated inverter temperature ({telem.inverter_temperature_c:.1f}°C)")
    else:
        deduct = max(0, (telem.inverter_temperature_c - 45) / 20 * 10)
    score -= deduct

    # Efficiency degradation (max deduction: 35 pts)
    baseline_eff = 0.185
    eff_drop = max(0, baseline_eff - telem.efficiency)
    eff_deduct = min(35.0, (eff_drop / baseline_eff) * 80)
    if eff_drop > 0.02:
        factors.append(f"Efficiency degradation ({telem.efficiency:.3f} vs baseline {baseline_eff})")
    score -= eff_deduct

    # Power ratio (max deduction: 25 pts — only when irradiance present)
    if telem.irradiance_w_m2 > 50:
        solar_factor = min(1.0, telem.irradiance_w_m2 / 1000.0)
        expected = capacity_kw * solar_factor
        pr = (telem.power_kw / expected * 100) if expected > 0 else 100
        if pr < 60:
            deduct_pr = 25.0
            factors.append(f"Low performance ratio ({pr:.1f}%)")
        elif pr < 80:
            deduct_pr = (80 - pr) / 20 * 25
            factors.append(f"Reduced performance ratio ({pr:.1f}%)")
        else:
            deduct_pr = 0
        score -= deduct_pr

    score = max(0.0, min(100.0, score))

    if score >= 75:
        risk = MaintenanceRisk.LOW
    elif score >= 50:
        risk = MaintenanceRisk.MEDIUM
    elif score >= 25:
        risk = MaintenanceRisk.HIGH
    else:
        risk = MaintenanceRisk.CRITICAL

    return round(score, 1), risk, factors


def _wind_health_score(asset_id: str, capacity_kw: float) -> tuple[float, MaintenanceRisk, list[str]]:
    ts = datetime.now(timezone.utc)
    telem = simulate_wind_telemetry(asset_id, capacity_kw, ts)
    factors: list[str] = []
    score = 100.0

    # Generator temperature (max deduction: 40 pts)
    if telem.generator_temperature_c >= 105:
        deduct = 40.0
        factors.append(f"Critical generator temperature ({telem.generator_temperature_c:.1f}°C)")
    elif telem.generator_temperature_c >= 80:
        deduct = 15.0 + (telem.generator_temperature_c - 80) / 25 * 25
        factors.append(f"Elevated generator temperature ({telem.generator_temperature_c:.1f}°C)")
    else:
        deduct = max(0, (telem.generator_temperature_c - 55) / 25 * 10)
    score -= deduct

    # Vibration (max deduction: 35 pts)
    if telem.vibration_mm_s >= 6.0:
        deduct_v = 35.0
        factors.append(f"Critical vibration ({telem.vibration_mm_s:.2f} mm/s)")
    elif telem.vibration_mm_s >= 3.5:
        deduct_v = 10.0 + (telem.vibration_mm_s - 3.5) / 2.5 * 25
        factors.append(f"Elevated vibration ({telem.vibration_mm_s:.2f} mm/s)")
    else:
        deduct_v = max(0, (telem.vibration_mm_s - 1.5) / 2.0 * 8)
    score -= deduct_v

    # RPM stability proxy (max deduction: 15 pts)
    expected_rpm = 15.0 + telem.wind_speed_ms * 1.2
    rpm_dev = abs(telem.turbine_rpm - expected_rpm) / max(expected_rpm, 1)
    if rpm_dev > 0.15:
        score -= min(15.0, rpm_dev * 50)
        factors.append(f"RPM deviation from expected ({telem.turbine_rpm:.0f} RPM, expected ~{expected_rpm:.0f})")

    # Efficiency (max deduction: 10 pts)
    if telem.efficiency < 0.30:
        score -= 10.0
        factors.append(f"Low turbine efficiency ({telem.efficiency:.2f})")

    score = max(0.0, min(100.0, score))

    if score >= 75:
        risk = MaintenanceRisk.LOW
    elif score >= 50:
        risk = MaintenanceRisk.MEDIUM
    elif score >= 25:
        risk = MaintenanceRisk.HIGH
    else:
        risk = MaintenanceRisk.CRITICAL

    return round(score, 1), risk, factors


# ---------------------------------------------------------------------------
# Public agent functions
# ---------------------------------------------------------------------------

def get_asset_health(asset_id: str) -> AssetHealth | None:
    t0 = time.perf_counter()
    asset = get_asset(asset_id)
    if not asset:
        return None

    ts = datetime.now(timezone.utc)

    if asset.asset_type in (AssetType.SOLAR_INVERTER, AssetType.SOLAR_PANEL):
        score, risk, factors = _solar_health_score(asset_id, asset.capacity_kw)
    elif asset.asset_type == AssetType.WIND_TURBINE:
        score, risk, factors = _wind_health_score(asset_id, asset.capacity_kw)
    else:
        score, risk, factors = 95.0, MaintenanceRisk.LOW, []

    log_event(
        "asset_health_calculated",
        category="agent",
        agent="PredictiveMaintenanceAgent",
        asset_id=asset_id,
        duration_ms=(time.perf_counter() - t0) * 1000,
        data_source="SIMULATED",
        extra={"health_score": score, "risk": risk},
    )

    return AssetHealth(
        asset_id=asset_id,
        health_score=score,
        maintenance_risk=risk,
        contributing_factors=factors,
        timestamp=ts,
        data_source=DataSource.SIMULATED,
    )


def get_maintenance_risks() -> list[AssetHealth]:
    """Return health scores for all solar inverters and wind turbines."""
    results = []
    for asset in list_assets():
        if asset.asset_type in (AssetType.SOLAR_INVERTER, AssetType.WIND_TURBINE):
            health = get_asset_health(asset.asset_id)
            if health:
                results.append(health)
    # Sort by health score ascending (worst first)
    results.sort(key=lambda h: h.health_score)
    return results
