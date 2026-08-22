"""Alert generation service — shared by api/alerts and agents."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.schemas import Alert, AlertSeverity
from app.simulation.engine import (
    SimulationScenario,
    get_scenario,
    simulate_solar_telemetry,
    simulate_wind_telemetry,
)
from app.models.asset_registry import get_asset


def generate_alerts() -> list[Alert]:
    """Dynamically generate alerts based on current simulation state."""
    alerts: list[Alert] = []
    scenario = get_scenario()
    ts = datetime.now(timezone.utc)

    # --- SOL-INV-042 degradation alert ---
    if scenario == SimulationScenario.SOLAR_INVERTER_DEGRADATION:
        asset = get_asset("SOL-INV-042")
        if asset:
            telem = simulate_solar_telemetry("SOL-INV-042", asset.capacity_kw, ts)
            perf_ratio = (telem.power_kw / asset.capacity_kw) * 100 if asset.capacity_kw else 0
            severity = AlertSeverity.WARNING if perf_ratio > 65 else AlertSeverity.HIGH

            alerts.append(Alert(
                alert_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"SOL-INV-042-{ts.date()}")),
                asset_id="SOL-INV-042",
                timestamp=ts,
                severity=severity,
                category="PERFORMANCE",
                description=f"Solar inverter SOL-INV-042 is producing {perf_ratio:.1f}% of expected output.",
                evidence=[
                    f"Actual power: {telem.power_kw:.1f} kW (expected: {asset.capacity_kw:.0f} kW)",
                    f"Inverter temperature: {telem.inverter_temperature_c:.1f}°C (threshold: 65°C)",
                    f"Efficiency: {telem.efficiency:.3f} (baseline: 0.185)",
                ],
                recommendation="Inspect inverter thermal and electrical systems. Check cooling system.",
                status="OPEN",
            ))

    # --- WT-017 overheating alert ---
    if scenario == SimulationScenario.WIND_TURBINE_OVERHEATING:
        asset = get_asset("WT-017")
        if asset:
            telem = simulate_wind_telemetry("WT-017", asset.capacity_kw, ts)
            severity = AlertSeverity.CRITICAL if telem.generator_temperature_c > 105 else AlertSeverity.HIGH

            alerts.append(Alert(
                alert_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"WT-017-{ts.date()}")),
                asset_id="WT-017",
                timestamp=ts,
                severity=severity,
                category="MAINTENANCE",
                description="Wind turbine WT-017 shows abnormal generator temperature and vibration.",
                evidence=[
                    f"Generator temperature: {telem.generator_temperature_c:.1f}°C (threshold: 85°C)",
                    f"Vibration: {telem.vibration_mm_s:.2f} mm/s (threshold: 3.5 mm/s)",
                    f"Power output: {telem.power_kw:.1f} kW",
                ],
                recommendation="Schedule immediate technical inspection. Monitor every 15 minutes.",
                status="OPEN",
            ))

    return alerts
