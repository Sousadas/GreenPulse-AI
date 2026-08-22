"""
Grid Integration Optimization Agent

Monitors generation vs demand, calculates surplus/deficit,
and produces advisory recommendations. Clearly labelled AI RECOMMENDATION —
this system does NOT directly control the grid.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.simulation.engine import simulate_grid_status
from app.observability.logger import log_event


def get_grid_recommendation() -> dict[str, Any]:
    """Compute grid balance and return an advisory recommendation."""
    t0 = time.perf_counter()
    grid = simulate_grid_status()
    ts = datetime.now(timezone.utc)

    surplus = grid.renewable_surplus_mw
    gen = grid.renewable_generation_mw
    load = grid.grid_load_mw
    renewable_pct = (gen / load * 100) if load > 0 else 0

    # Determine recommendation
    if surplus > 5.0:
        action = "EXPORT"
        recommendation = (
            f"AI RECOMMENDATION: Renewable surplus of {surplus:.2f} MW available. "
            f"Recommended action: Export to grid and/or charge available storage assets."
        )
        priority = "MEDIUM"
    elif surplus > 2.0:
        action = "EXPORT_PARTIAL"
        recommendation = (
            f"AI RECOMMENDATION: Moderate renewable surplus of {surplus:.2f} MW. "
            f"Recommended action: Export surplus to grid."
        )
        priority = "LOW"
    elif surplus < -5.0:
        action = "IMPORT"
        recommendation = (
            f"AI RECOMMENDATION: Generation deficit of {abs(surplus):.2f} MW. "
            f"Recommended action: Increase grid import or reduce curtailment. "
            f"Investigate underperforming assets."
        )
        priority = "HIGH"
    elif surplus < -2.0:
        action = "IMPORT_PARTIAL"
        recommendation = (
            f"AI RECOMMENDATION: Small generation deficit of {abs(surplus):.2f} MW. "
            f"Recommended action: Monitor closely. Prepare supplemental grid import if deficit increases."
        )
        priority = "MEDIUM"
    else:
        action = "BALANCED"
        recommendation = (
            f"AI RECOMMENDATION: Generation closely matches demand (surplus: {surplus:+.2f} MW). "
            f"Recommended action: Maintain current operation."
        )
        priority = "LOW"

    log_event(
        "grid_recommendation",
        category="agent",
        agent="GridIntegrationAgent",
        duration_ms=(time.perf_counter() - t0) * 1000,
        data_source="SIMULATED",
        extra={"action": action, "surplus_mw": surplus},
    )

    return {
        "timestamp": ts.isoformat(),
        "renewable_generation_mw": round(gen, 3),
        "grid_load_mw": round(load, 3),
        "renewable_surplus_mw": round(surplus, 3),
        "grid_export_mw": round(grid.grid_export_mw, 3),
        "grid_import_mw": round(grid.grid_import_mw, 3),
        "renewable_percentage": round(renewable_pct, 1),
        "grid_frequency_hz": round(grid.grid_frequency_hz, 3),
        "grid_voltage_kv": round(grid.grid_voltage_v / 1000, 2),
        "action": action,
        "priority": priority,
        "recommendation": recommendation,
        "data_source": "SIMULATED",
    }
