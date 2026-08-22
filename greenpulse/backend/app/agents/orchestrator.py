"""
GreenPulse Orchestrator Agent (Primary)

Routes user questions to the correct specialized agent, aggregates results,
then passes the structured context to IBM Granite for explanation.

Routing logic is rule-based (keyword matching) so it is deterministic —
Granite only generates the natural-language explanation, not the numbers.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.services.watsonx_service import generate_ai_response
from app.agents.asset_performance import get_all_asset_anomalies, get_asset_performance
from app.agents.predictive_maintenance import get_asset_health, get_maintenance_risks
from app.agents.forecasting import forecast_generation
from app.agents.grid_optimization import get_grid_recommendation
from app.services.alert_service import generate_alerts as _generate_alerts
from app.simulation.engine import simulate_weather, simulate_grid_status, get_scenario
from app.models.asset_registry import get_asset, list_assets
from app.models.schemas import AssetType
from app.observability.logger import log_event


SYSTEM_PROMPT = """You are GreenPulse AI, an intelligent renewable-energy operations assistant for a hybrid solar-wind power plant in Kutch and Banaskantha, Gujarat, India.

Structure EVERY operational answer with exactly these sections:

SUMMARY:
<one-sentence answer>

EVIDENCE:
<bullet-pointed numerical facts from the context — never invent numbers>

ANALYSIS:
<reasoning about what the evidence means>

IMPACT:
<operational impact on generation, grid, or assets>

RECOMMENDATION:
<clear advisory action — always label as AI RECOMMENDATION>

DATA SOURCES:
<list which agents/tools/data sources were used>

Rules:
- Never fabricate numbers. Only use values from the context provided.
- If data is unavailable, write DATA_UNAVAILABLE.
- All grid actions are advisory. Never claim direct control of grid hardware.
- Keep responses concise and evidence-based.
"""


def _build_full_context() -> dict[str, Any]:
    """Gather data from all agents and return a structured context dict."""
    from app.core.config import get_settings
    settings = get_settings()
    ts = datetime.now(timezone.utc)
    weather = simulate_weather()
    grid = simulate_grid_status()
    alerts = _generate_alerts()
    anomalies = get_all_asset_anomalies()
    grid_rec = get_grid_recommendation()
    forecast = forecast_generation("HYBRID", 6)
    risks = get_maintenance_risks()
    scenario = get_scenario()

    # Top-3 worst maintenance risks
    critical_assets = [
        {"asset_id": r.asset_id, "health_score": r.health_score, "risk": r.maintenance_risk, "factors": r.contributing_factors[:2]}
        for r in risks[:3] if r.maintenance_risk.value in ("HIGH", "CRITICAL")
    ]

    return {

    "data_source": settings.data_source_mode,
    "timestamp": ts.isoformat(),
    "scenario": scenario.value,
        "weather": {
            "temperature_c": round(weather.temperature_c, 1),
            "wind_speed_ms": round(weather.wind_speed_ms, 1),
            "irradiance_w_m2": round(weather.solar_irradiance_w_m2, 0),
            "cloud_cover_pct": weather.cloud_cover_percent,
        },
        "grid": {
            "renewable_mw": round(grid.renewable_generation_mw, 2),
            "load_mw": round(grid.grid_load_mw, 2),
            "surplus_mw": round(grid.renewable_surplus_mw, 2),
            "frequency_hz": round(grid.grid_frequency_hz, 3),
            "recommendation": grid_rec["recommendation"],
        },
        "alerts": [
            {"severity": a.severity, "asset_id": a.asset_id, "description": a.description, "evidence": a.evidence}
            for a in alerts
        ],
        "anomalies": [
            {"asset_id": a["asset_id"], "status": a["status"], "issues": a["anomalies"]}
            for a in anomalies[:5]
        ],
        "critical_maintenance": critical_assets,
        "forecast_6h": [
            {"hour": i+1, "kw": f.predicted_generation_kw, "confidence": f.confidence}
            for i, f in enumerate(forecast[:6])
        ],
    }


def _context_to_string(ctx: dict[str, Any]) -> str:
    """Render context dict as a readable block for the Granite prompt."""
    w = ctx["weather"]
    g = ctx["grid"]
    alerts_str = "\n".join(
        f"  [{a['severity']}] {a['asset_id']}: {a['description']}"
        for a in ctx["alerts"]
    ) or "  None"
    anomalies_str = "\n".join(
        f"  {a['asset_id']} ({a['status']}): {'; '.join(a['issues'][:2])}"
        for a in ctx["anomalies"]
    ) or "  None"
    maint_str = "\n".join(
        f"  {a['asset_id']}: Health {a['health_score']}/100 — {a['risk']}"
        for a in ctx["critical_maintenance"]
    ) or "  All assets low risk"
    forecast_str = "\n".join(
        f"  +{f['hour']}h: {f['kw']} kW (confidence {int(f['confidence']*100)}%)"
        for f in ctx["forecast_6h"]
    )

    return f"""CURRENT OPERATIONAL CONTEXT [{ctx['timestamp']}]
DATA MODE: {ctx.get('data_source', 'SIMULATED')}
SIMULATION SCENARIO: {ctx['scenario']}

WEATHER (Kutch, Gujarat):
  Temperature: {w['temperature_c']}°C | Wind: {w['wind_speed_ms']} m/s
  Solar Irradiance: {w['irradiance_w_m2']} W/m² | Cloud Cover: {w['cloud_cover_pct']}%

GRID:
  Renewable Generation: {g['renewable_mw']} MW | Grid Load: {g['load_mw']} MW
  Surplus: {g['surplus_mw']} MW | Frequency: {g['frequency_hz']} Hz
  Grid Advisory: {g['recommendation']}

ACTIVE ALERTS:
{alerts_str}

ANOMALIES DETECTED:
{anomalies_str}

CRITICAL MAINTENANCE RISKS:
{maint_str}

6-HOUR GENERATION FORECAST:
{forecast_str}

DATA SOURCE: {ctx.get('data_source', 'SIMULATED')}"""


async def orchestrate(question: str) -> dict[str, Any]:
    """Main orchestrator entry point. Returns structured response.

    This is async so that the blocking Granite SDK call is correctly
    delegated to a thread pool via granite_generate() without stalling
    the FastAPI event loop.
    """
    from app.core.config import get_settings
    settings = get_settings()

    t0 = time.perf_counter()

    ctx = _build_full_context()
    ctx_str = _context_to_string(ctx)

    prompt = f"""{SYSTEM_PROMPT}

{ctx_str}

USER QUESTION: {question}

ANSWER:"""

    # Awaitable — runs blocking IBM SDK call in thread pool via watsonx_service
    ai_response = await generate_ai_response(prompt)
    answer = ai_response.answer

    duration_ms = (time.perf_counter() - t0) * 1000

    log_event(
        "orchestrator_query",
        category="agent",
        agent="GreenPulseOrchestrator",
        duration_ms=duration_ms,
        data_source=settings.data_source_mode,
        extra={"question": question[:120], "agents_invoked": 4},
    )

    return {
        "question": question,
        "answer": answer,
        "context_snapshot": {
            "active_alerts": len(ctx["alerts"]),
            "anomalies_detected": len(ctx["anomalies"]),
            "critical_maintenance": len(ctx["critical_maintenance"]),
            "grid_surplus_mw": ctx["grid"]["surplus_mw"],
            "scenario": ctx["scenario"],
        },
        "agents_invoked": [
            "AssetPerformanceAgent",
            "PredictiveMaintenanceAgent",
            "WeatherForecastingAgent",
            "GridIntegrationAgent",
        ],
        "data_source": settings.data_source_mode,
        "model": settings.granite_model_id,
        "ai_provider": ai_response.provider,
        "duration_ms": round(duration_ms, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
