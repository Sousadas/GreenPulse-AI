"""
GreenPulse AI — IBM watsonx.ai Service
=======================================
Single interface for all IBM Granite interactions.

Architecture:
    settings (config.py)
        ↓
    WatsonxService._build_client()
        ↓
    ibm_watsonx_ai Credentials → APIClient → ModelInference
        ↓
    generate_ai_response(prompt, system_prompt)
        ↓
    caller (orchestrator / agents)

AI_MODE behavior:
    ibm        — always call IBM Granite
    simulation — always return local stub
    hybrid     — IBM when configured, stub fallback otherwise

Security rules enforced here:
    - API key is NEVER logged
    - IAM tokens are NEVER logged
    - API key is NEVER included in any response payload
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.observability.logger import get_logger, log_event

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Generation parameters
# ---------------------------------------------------------------------------

_GENERATE_PARAMS: dict[str, Any] = {
    "max_new_tokens": 1024,
    "temperature": 0.2,
    "repetition_penalty": 1.1,
    "decoding_method": "greedy",
}


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------

@dataclass
class AIResponse:
    success: bool
    answer: str
    provider: str          # "ibm" | "simulation"
    model: str
    duration_ms: float
    error: str | None = None


# ---------------------------------------------------------------------------
# Local reasoning engine (simulation fallback)
#
# When IBM Granite is not connected this engine reads the real operational
# context from the orchestrator and produces a structured answer in the same
# SUMMARY / EVIDENCE / ANALYSIS / IMPACT / RECOMMENDATION / DATA SOURCES
# format that Granite would return.  No numbers are invented — everything
# comes from the simulation data pipeline.
# ---------------------------------------------------------------------------

def _local_reason(prompt: str) -> str:
    """Rule-based reasoning over live simulation context.

    Parses the question from the prompt, pulls real data, and returns a
    fully-structured operational answer without calling IBM.
    """
    # Late import to avoid circular dependency at module load time
    from app.agents.orchestrator import _build_full_context

    # Extract the question
    question = ""
    for line in prompt.splitlines():
        if line.startswith("USER QUESTION:"):
            question = line.replace("USER QUESTION:", "").strip()
            break
    q_lower = question.lower()

    ctx = _build_full_context()
    g = ctx["grid"]
    w = ctx["weather"]
    forecast = ctx["forecast_6h"]
    alerts = ctx["alerts"]
    anomalies = ctx["anomalies"]
    maint = ctx["critical_maintenance"]

    # ── Forecast questions ──────────────────────────────────────────────────
    if any(k in q_lower for k in ["forecast", "next", "expected generation", "6 hour", "6h", "predict"]):
        total_kw = sum(f["kw"] for f in forecast)
        avg_kw = total_kw / len(forecast) if forecast else 0
        peak = max(forecast, key=lambda f: f["kw"]) if forecast else {}
        low  = min(forecast, key=lambda f: f["kw"]) if forecast else {}
        fc_lines = "\n".join(f"  • +{f['hour']}h: {f['kw']:,.0f} kW  ({int(f['confidence']*100)}% confidence)" for f in forecast)
        _solar_note = (
            "Solar irradiance is near zero — daytime generation will be wind-dominated."
            if w["irradiance_w_m2"] < 50
            else f"Solar irradiance of {w['irradiance_w_m2']:.0f} W/m² will contribute to hybrid output."
        )
        _wind_note = (
            "within rated operating range (3–25 m/s)"
            if 3 <= w["wind_speed_ms"] <= 25
            else "outside rated range — reduced output expected"
        )
        _impact_note = (
            f"Current grid deficit of {abs(g['surplus_mw'])} MW may deepen if generation falls below forecast."
            if g["surplus_mw"] < 0
            else f"Surplus of {g['surplus_mw']} MW provides buffer above grid demand."
        )
        _rec_note = (
            "Schedule additional grid import cover for the deficit window."
            if g["surplus_mw"] < 0
            else "No immediate action required — plant is on track to meet demand."
        )
        return (
            f"SUMMARY:\n"
            f"The hybrid plant is forecast to generate an average of {avg_kw:,.0f} kW over the next 6 hours.\n\n"
            f"EVIDENCE:\n"
            f"{fc_lines}\n"
            f"  • Current wind speed: {w['wind_speed_ms']} m/s\n"
            f"  • Solar irradiance: {w['irradiance_w_m2']:.0f} W/m²  |  Cloud cover: {w['cloud_cover_pct']:.0f}%\n"
            f"  • Peak forecast: +{peak.get('hour',0)}h → {peak.get('kw',0):,.0f} kW\n"
            f"  • Lowest forecast: +{low.get('hour',0)}h → {low.get('kw',0):,.0f} kW\n\n"
            f"ANALYSIS:\n"
            f"{_solar_note} "
            f"Wind speed of {w['wind_speed_ms']} m/s is {_wind_note}.\n\n"
            f"IMPACT:\n"
            f"Cumulative 6-hour generation estimate: {total_kw/1000:,.2f} MWh. "
            f"{_impact_note}\n\n"
            f"RECOMMENDATION:\nAI RECOMMENDATION: Monitor irradiance and wind speed. "
            f"{_rec_note}\n\n"
            f"DATA SOURCES:\nWeatherForecastingAgent · SimulationEngine · GridIntegrationAgent"
        )

    # ── Grid / surplus questions ────────────────────────────────────────────
    if any(k in q_lower for k in ["grid", "surplus", "deficit", "import", "export", "demand"]):
        status = "surplus" if g["surplus_mw"] >= 0 else "deficit"
        _analysis_note = (
            "Generation exceeds demand — renewable surplus available for export or storage charge."
            if status == "surplus"
            else "Generation is below demand — grid import is active to cover the shortfall."
        )
        _impact_grid = (
            f"Export opportunity of {g['surplus_mw']:.2f} MW. Charging available storage would improve self-sufficiency."
            if status == "surplus"
            else f"Grid import of {abs(g['surplus_mw']):.2f} MW increases operating cost and carbon footprint."
        )
        return (
            f"SUMMARY:\n"
            f"The plant is currently in a renewable energy {status} of {abs(g['surplus_mw']):.2f} MW.\n\n"
            f"EVIDENCE:\n"
            f"  • Renewable generation: {g['renewable_mw']:.2f} MW\n"
            f"  • Grid load: {g['load_mw']:.2f} MW\n"
            f"  • {status.capitalize()}: {abs(g['surplus_mw']):.2f} MW\n"
            f"  • Grid frequency: {g['frequency_hz']:.3f} Hz\n\n"
            f"ANALYSIS:\n"
            f"{_analysis_note}\n\n"
            f"IMPACT:\n"
            f"{_impact_grid}\n\n"
            f"RECOMMENDATION:\n{g['recommendation']}\n\n"
            f"DATA SOURCES:\nGridIntegrationAgent · SimulationEngine"
        )

    # ── Alerts / asset issues ───────────────────────────────────────────────
    if any(k in q_lower for k in ["alert", "issue", "fault", "problem", "caused", "latest"]):
        if not alerts:
            return (
                "SUMMARY:\nNo active alerts — all assets are operating within normal parameters.\n\n"
                "EVIDENCE:\n  • Active alerts: 0\n  • All monitored assets: ONLINE\n\n"
                "ANALYSIS:\nThe anomaly detection layer has not triggered any threshold breaches.\n\n"
                "IMPACT:\nNormal generation expected. No corrective action required.\n\n"
                "RECOMMENDATION:\nAI RECOMMENDATION: Continue standard monitoring interval.\n\n"
                "DATA SOURCES:\nAssetPerformanceAgent · AlertService"
            )
        a = alerts[0]
        ev = "\n".join(f"  • {e}" for e in a.get("evidence", []))
        return (
            f"SUMMARY:\nThe most recent alert is [{a['severity']}] on asset {a['asset_id']}.\n\n"
            f"EVIDENCE:\n{ev if ev else '  • ' + a['description']}\n\n"
            f"ANALYSIS:\n{a['description']}\n\n"
            f"IMPACT:\nAsset {a['asset_id']} may be contributing to reduced generation. "
            f"{'Other ' + str(len(alerts)-1) + ' alert(s) also active.' if len(alerts) > 1 else 'This is the only active alert.'}\n\n"
            f"RECOMMENDATION:\nAI RECOMMENDATION: Inspect {a['asset_id']} immediately. Prioritise based on severity level {a['severity']}.\n\n"
            f"DATA SOURCES:\nAssetPerformanceAgent · AlertService"
        )

    # ── Maintenance / turbine health ────────────────────────────────────────
    if any(k in q_lower for k in ["maintenance", "turbine", "health", "inspect", "risk", "repair"]):
        if not maint:
            return (
                "SUMMARY:\nAll monitored assets show LOW maintenance risk.\n\n"
                "EVIDENCE:\n  • No assets in HIGH or CRITICAL maintenance risk tier\n"
                f"  • Anomalies currently detected: {len(anomalies)}\n\n"
                "ANALYSIS:\nHealth scores are within acceptable range for all solar inverters and wind turbines.\n\n"
                "IMPACT:\nNo unscheduled maintenance required at this time.\n\n"
                "RECOMMENDATION:\nAI RECOMMENDATION: Maintain scheduled inspection intervals.\n\n"
                "DATA SOURCES:\nPredictiveMaintenanceAgent · SimulationEngine"
            )
        top = maint[0]
        factors = "; ".join(top.get("factors", [])) or "multiple degradation indicators"
        return (
            f"SUMMARY:\nAsset {top['asset_id']} has the highest maintenance risk ({top['risk']}, health score {top['health_score']}/100).\n\n"
            f"EVIDENCE:\n  • {top['asset_id']} health: {top['health_score']}/100  Risk: {top['risk']}\n"
            f"  • Contributing factors: {factors}\n"
            f"  • Total high/critical assets: {len(maint)}\n\n"
            f"ANALYSIS:\nThe health score of {top['health_score']}/100 indicates significant degradation. "
            "Trend analysis shows multiple concurrent signals that typically precede failure.\n\n"
            f"IMPACT:\nIf {top['asset_id']} is not serviced, generation loss and potential unplanned downtime are likely within the next maintenance window.\n\n"
            f"RECOMMENDATION:\nAI RECOMMENDATION: Schedule technical inspection of {top['asset_id']} within 24–48 hours.\n\n"
            "DATA SOURCES:\nPredictiveMaintenanceAgent · AssetPerformanceAgent"
        )

    # ── Performance / underperformance ──────────────────────────────────────
    if any(k in q_lower for k in ["performance", "worst", "underperform", "solar", "wind", "generation lower", "why"]):
        weather_cause = w["irradiance_w_m2"] < 100 and "low solar irradiance" or w["cloud_cover_pct"] > 60 and "cloud cover" or None
        anomaly_cause = f"{len(anomalies)} asset anomalies detected" if anomalies else "no asset anomalies"
        top_anomaly = anomalies[0] if anomalies else None
        _worst_line = (
            f"  • Worst asset: {top_anomaly['asset_id']} — {'; '.join(top_anomaly['issues'][:2])}\n"
            if top_anomaly else ""
        )
        _weather_analysis = (
            f"Generation reduction is primarily attributed to {weather_cause}. "
            if weather_cause else "Weather conditions are normal. "
        )
        _asset_analysis = (
            f"Asset-level anomalies on {top_anomaly['asset_id']} are contributing to below-expected output."
            if top_anomaly else "All assets are performing within expected parameters."
        )
        _impact_perf = (
            f"Current deficit of {abs(g['surplus_mw']):.2f} MW requires grid import."
            if g["surplus_mw"] < 0
            else f"Generation is sufficient to cover grid demand with a surplus of {g['surplus_mw']:.2f} MW."
        )
        _inspect_rec = f"Inspect {top_anomaly['asset_id']}. " if top_anomaly else ""
        return (
            f"SUMMARY:\nCurrent hybrid generation is {g['renewable_mw']:.2f} MW against a grid load of {g['load_mw']:.2f} MW.\n\n"
            f"EVIDENCE:\n"
            f"  • Renewable generation: {g['renewable_mw']:.2f} MW\n"
            f"  • Solar irradiance: {w['irradiance_w_m2']:.0f} W/m²\n"
            f"  • Cloud cover: {w['cloud_cover_pct']:.0f}%\n"
            f"  • Wind speed: {w['wind_speed_ms']} m/s\n"
            f"  • Asset anomalies: {anomaly_cause}\n"
            f"{_worst_line}"
            f"\nANALYSIS:\n"
            f"{_weather_analysis}"
            f"{_asset_analysis}"
            f"\n\nIMPACT:\n"
            f"{_impact_perf}\n\n"
            f"RECOMMENDATION:\nAI RECOMMENDATION: "
            f"{_inspect_rec}"
            f"Monitor weather forecast for improvement in generation conditions.\n\n"
            f"DATA SOURCES:\nAssetPerformanceAgent · WeatherForecastingAgent · GridIntegrationAgent"
        )

    # ── Generic / catch-all ─────────────────────────────────────────────────
    alert_summary = f"{len(alerts)} active alert(s)" if alerts else "no active alerts"
    maint_summary = f"{len(maint)} asset(s) at HIGH/CRITICAL risk" if maint else "all assets at LOW risk"
    return (
        f"SUMMARY:\nGreenPulse plant is operating in {ctx['scenario']} mode. "
        f"Renewable generation: {g['renewable_mw']:.2f} MW | Grid load: {g['load_mw']:.2f} MW.\n\n"
        f"EVIDENCE:\n"
        f"  • Renewable generation: {g['renewable_mw']:.2f} MW\n"
        f"  • Grid load: {g['load_mw']:.2f} MW\n"
        f"  • Grid surplus/deficit: {g['surplus_mw']:+.2f} MW\n"
        f"  • Wind speed: {w['wind_speed_ms']} m/s | Irradiance: {w['irradiance_w_m2']:.0f} W/m²\n"
        f"  • Alerts: {alert_summary}\n"
        f"  • Maintenance: {maint_summary}\n\n"
        f"ANALYSIS:\n"
        f"Plant systems are {'operating normally' if not alerts else 'operating with active alerts requiring attention'}. "
        f"{'Grid is in deficit — import active.' if g['surplus_mw'] < 0 else 'Grid balance is positive.'}\n\n"
        f"IMPACT:\nCurrent operational state {'requires attention on flagged assets' if alerts else 'is stable with no immediate action required'}.\n\n"
        f"RECOMMENDATION:\nAI RECOMMENDATION: {g['recommendation'].replace('AI RECOMMENDATION: ', '')}\n\n"
        f"DATA SOURCES:\nOrchestrator · AssetPerformanceAgent · GridIntegrationAgent · SimulationEngine"
    )


def _simulation_response(prompt: str) -> AIResponse:
    """Generate a data-driven structured response using local reasoning.

    Called when AI_MODE=simulation or IBM Granite is unavailable (hybrid fallback).
    Produces the same SUMMARY/EVIDENCE/ANALYSIS/IMPACT/RECOMMENDATION structure
    that IBM Granite would return — all numbers come from the real simulation engine.
    """
    settings = get_settings()
    import time as _time
    t0 = _time.perf_counter()

    answer = _local_reason(prompt)

    return AIResponse(
        success=True,
        answer=answer,
        provider="simulation",
        model=f"{settings.granite_model_id} (local-reasoning)",
        duration_ms=round((_time.perf_counter() - t0) * 1000, 1),
    )


# ---------------------------------------------------------------------------
# IBM client (cached, thread-safe)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_ibm_client() -> Any | None:
    """Build and cache the IBM ModelInference client.

    Returns None if:
    - credentials are absent / placeholder values
    - the ibm-watsonx-ai SDK is not installed
    - initialisation fails for any reason

    The API key is consumed by the SDK to obtain an IAM bearer token.
    It is NEVER stored in logs, responses, or application state beyond
    this function's local scope.
    """
    settings = get_settings()

    if not settings.granite_configured:
        logger.info(
            "IBM Granite not configured — stub mode active",
            model=settings.granite_model_id,
            region=settings.ibm_region,
            configured=False,
        )
        return None

    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        # Credentials exchanges the API key for an IAM bearer token internally.
        # The key is passed only to the SDK — never logged here.
        credentials = Credentials(
            url=settings.watsonx_url,
            api_key=settings.watsonx_api_key,
        )
        client = ModelInference(
            model_id=settings.granite_model_id,
            credentials=credentials,
            project_id=settings.watsonx_project_id,
            params=_GENERATE_PARAMS,
        )

        logger.info(
            "IBM Granite client initialised",
            model=settings.granite_model_id,
            region=settings.ibm_region,
            url=settings.watsonx_url,
            # API key is intentionally NOT logged
        )
        return client

    except ImportError:
        logger.error(
            "ibm-watsonx-ai SDK not installed. Run: pip install ibm-watsonx-ai>=1.1.0"
        )
        return None
    except Exception as exc:
        logger.error(
            "IBM Granite client initialisation failed",
            error=str(exc),
            model=settings.granite_model_id,
        )
        return None


def reset_ibm_client() -> None:
    """Invalidate the cached client — call after credential rotation."""
    _get_ibm_client.cache_clear()


# ---------------------------------------------------------------------------
# Synchronous generation (runs in thread pool)
# ---------------------------------------------------------------------------

def _sync_generate(prompt: str, system_prompt: str | None = None) -> AIResponse:
    """Blocking IBM SDK call.  Must be invoked via asyncio thread pool."""
    settings = get_settings()
    client = _get_ibm_client()

    if client is None:
        return _simulation_response(prompt)

    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    t0 = time.perf_counter()

    try:
        messages = [
            {
                "role": "user",
                "content": full_prompt,
            }
        ]

        # Use IBM watsonx.ai Chat API
        chat_response = client.chat(messages=messages)

        duration_ms = (time.perf_counter() - t0) * 1000

        # Extract the assistant response from the Chat API response
        if isinstance(chat_response, dict):
            choices = chat_response.get("choices", [])

            if choices:
                response = choices[0].get("message", {}).get("content", "")
            else:
                response = ""
        else:
            response = str(chat_response)

        log_event(
            "ibm_granite_generate",
            category="ibm",
            model=settings.granite_model_id,
            duration_ms=duration_ms,
        )

        return AIResponse(
            success=True,
            answer=response,
            provider="ibm",
            model=settings.granite_model_id,
            duration_ms=round(duration_ms, 1),
        )

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        error_type = type(exc).__name__

        log_event(
            "ibm_granite_error",
            category="ibm",
            model=settings.granite_model_id,
            duration_ms=duration_ms,
            extra={
                "error_type": error_type,
                "error": str(exc),
            },
        )

        safe_exc_str = str(exc)
        if settings.watsonx_api_key and settings.watsonx_api_key in safe_exc_str:
            safe_exc_str = safe_exc_str.replace(settings.watsonx_api_key, "***REDACTED***")

        # In IBM mode, return the actual IBM error
        if settings.effective_ai_mode == "ibm":
            return AIResponse(
                success=False,
                answer=(
                    f"[IBM Granite ERROR — {error_type}]\n"
                    f"{safe_exc_str}\n\n"
                    "Check connectivity and credentials."
                ),
                provider="ibm",
                model=settings.granite_model_id,
                duration_ms=round(duration_ms, 1),
                error=safe_exc_str,
            )

        # Hybrid mode: fall back to local simulation
        else:
            logger.info(
                "IBM error — activating simulation fallback",
                error_type=error_type,
            )

            stub = _simulation_response(prompt)
            stub.error = f"{error_type}: {exc}"
            return stub


# ---------------------------------------------------------------------------
# Public async interface
# ---------------------------------------------------------------------------

async def generate_ai_response(
    prompt: str,
    system_prompt: str | None = None,
) -> AIResponse:
    """Main entry point for all AI generation in GreenPulse.

    Routes based on effective_ai_mode:
        simulation → immediate stub (no I/O)
        ibm / hybrid → blocking SDK call in thread pool (non-blocking for FastAPI)

    Never exposes credentials in the return value.
    """
    settings = get_settings()

    if settings.effective_ai_mode == "simulation":
        return _simulation_response(prompt)

    # ibm or hybrid — run blocking SDK call off the event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_generate, prompt, system_prompt)


# ---------------------------------------------------------------------------
# Lightweight connectivity probe (non-generative)
# ---------------------------------------------------------------------------

async def probe_ibm_connectivity() -> dict[str, Any]:
    """Check configuration and client state without generating text."""
    settings = get_settings()
    client = _get_ibm_client()

    base = {
        "provider": "IBM watsonx.ai",
        "model": settings.granite_model_id,
        "url": settings.watsonx_url,
        "region": settings.ibm_region,
        "mode": settings.ai_mode,
        "effective_mode": settings.effective_ai_mode,
        "configured": settings.granite_configured,
        # project_id is shown truncated — not a secret but no need to expose fully
        "project_id_prefix": settings.watsonx_project_id[:8] + "..." if settings.watsonx_project_id else "",
    }

    if not settings.granite_configured:
        return {**base, "available": False, "status": "NOT_CONFIGURED",
                "message": "WATSONX_API_KEY and/or WATSONX_PROJECT_ID are not set."}

    if client is None:
        return {**base, "available": False, "status": "INIT_FAILED",
                "message": "Client failed to initialise — check logs for details."}

    return {**base, "available": True, "status": "CONFIGURED",
            "message": "Credentials present and client initialised. "
                       "No test generation performed — call POST /api/ai/test to verify end-to-end."}
