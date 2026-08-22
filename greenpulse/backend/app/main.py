"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.observability.logger import get_logger
from app.api import assets, weather, grid, solar, wind, forecast, alerts, ai, simulation, maintenance, system

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "GreenPulse AI backend starting",
        env=settings.app_env,
        data_mode=settings.data_source_mode,
        granite_configured=bool(settings.watsonx_api_key),
    )
    yield
    logger.info("GreenPulse AI backend shutdown")


app = FastAPI(
    title="GreenPulse AI",
    description="Smart Renewable Energy Asset Monitoring — Kutch & Banaskantha, Gujarat",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(assets.router,      prefix="/api/assets",       tags=["Assets"])
app.include_router(solar.router,       prefix="/api/solar",        tags=["Solar"])
app.include_router(wind.router,        prefix="/api/wind",         tags=["Wind"])
app.include_router(weather.router,     prefix="/api/weather",      tags=["Weather"])
app.include_router(grid.router,        prefix="/api/grid",         tags=["Grid"])
app.include_router(forecast.router,    prefix="/api/forecast",     tags=["Forecast"])
app.include_router(alerts.router,      prefix="/api/alerts",       tags=["Alerts"])
app.include_router(maintenance.router, prefix="/api/maintenance",  tags=["Maintenance"])
app.include_router(ai.router,          prefix="/api/ai",           tags=["AI"])
app.include_router(simulation.router,  prefix="/api/simulation",   tags=["Simulation"])
app.include_router(system.router,      prefix="/api/system",       tags=["System"])

# /api/health/ai is registered on the ai router as GET /api/ai/health
# Expose it also at the convenient top-level path /api/health/ai
from app.api.ai import ai_health as _ai_health_fn
from fastapi import APIRouter as _AR
_health_shortcut = _AR()
_health_shortcut.add_api_route("/ai", _ai_health_fn, methods=["GET"], tags=["Health"])
app.include_router(_health_shortcut, prefix="/api/health")


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "service": "GreenPulse AI",
        "version": "0.2.0",
        "env": settings.app_env,
        "data_source_mode": settings.data_source_mode,
        "granite_configured": settings.granite_configured,
    }
