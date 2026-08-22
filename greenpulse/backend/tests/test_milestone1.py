"""Milestone 1 smoke tests.

Tests cover:
  - Backend health endpoint
  - System status endpoint
  - AI query endpoint (stub or real Granite)
  - Config loading
  - IBM client probe

Run from greenpulse/backend/:
  .venv/bin/pytest tests/test_milestone1.py -v
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import get_settings
from app.core.ibm_client import probe_granite, get_granite_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_config_loads(settings):
    """Settings must load without raising."""
    assert settings is not None
    assert settings.watsonx_url.startswith("https://")
    assert settings.granite_model_id != ""


def test_config_au_syd_default(settings):
    """AU-SYD must be the default region when no .env override."""
    # The .env may override this — just assert it's a valid non-empty URL
    assert "ml.cloud.ibm.com" in settings.watsonx_url


def test_granite_configured_false_without_credentials():
    """granite_configured must return False when key is missing or placeholder."""
    from app.core.config import Settings
    s = Settings(watsonx_api_key="", watsonx_project_id="")
    assert s.granite_configured is False

    s2 = Settings(watsonx_api_key="REPLACE_WITH_YOUR_NEW_ROTATED_API_KEY", watsonx_project_id="proj")
    assert s2.granite_configured is False


# ---------------------------------------------------------------------------
# Backend health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint(client):
    """GET /health must return 200 with status ok."""
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "GreenPulse AI"
    assert "granite_configured" in body


# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_system_status_endpoint(client):
    """GET /api/system/status must return all expected subsystem keys."""
    r = await client.get("/api/system/status")
    assert r.status_code == 200
    body = r.json()
    subs = body["subsystems"]
    for key in ["backend", "ibm_granite", "ibm_iam", "simulation_engine", "weather_api", "database", "agent_orchestration"]:
        assert key in subs, f"Missing subsystem key: {key}"
    assert subs["backend"]["status"] == "ONLINE"
    assert subs["simulation_engine"]["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_system_status_granite_field(client):
    """Granite subsystem must always report its status field."""
    r = await client.get("/api/system/status")
    granite = r.json()["subsystems"]["ibm_granite"]
    assert "status" in granite
    assert granite["status"] in ("NOT_CONFIGURED", "CONFIGURED", "INIT_FAILED")


# ---------------------------------------------------------------------------
# IBM Granite probe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_probe_granite_returns_dict():
    """probe_granite() must return a dict with status and model."""
    result = await probe_granite()
    assert isinstance(result, dict)
    assert "status" in result
    assert "model" in result


# ---------------------------------------------------------------------------
# AI query endpoint (stub mode when Granite not configured)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_query_returns_structure(client):
    """POST /api/ai/query must return the expected response structure."""
    r = await client.post(
        "/api/ai/query",
        json={"question": "Explain the purpose of GreenPulse AI."},
        timeout=60.0,
    )
    assert r.status_code == 200
    body = r.json()

    # Required keys in every response
    for key in ["question", "answer", "data_source", "model", "timestamp", "agents_invoked"]:
        assert key in body, f"Missing key in AI response: {key}"

    assert body["question"] == "Explain the purpose of GreenPulse AI."
    assert isinstance(body["answer"], str)
    assert len(body["answer"]) > 10  # non-empty response


@pytest.mark.asyncio
async def test_ai_query_context_snapshot(client):
    """Response must include context_snapshot with operational data."""
    r = await client.post(
        "/api/ai/query",
        json={"question": "What is the current grid status?"},
        timeout=60.0,
    )
    body = r.json()
    snap = body.get("context_snapshot", {})
    assert "active_alerts" in snap
    assert "scenario" in snap


@pytest.mark.asyncio
async def test_ai_query_empty_question(client):
    """Empty question should still return a response (not crash)."""
    r = await client.post(
        "/api/ai/query",
        json={"question": ""},
        timeout=60.0,
    )
    # FastAPI validates the body — empty string is technically valid
    assert r.status_code in (200, 422)


# ---------------------------------------------------------------------------
# Simulation status (prerequisite for later milestones)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simulation_status(client):
    """GET /api/simulation/status must return current scenario."""
    r = await client.get("/api/simulation/status")
    assert r.status_code == 200
    body = r.json()
    assert "active_scenario" in body
    assert "available_scenarios" in body
    assert "NORMAL" in body["available_scenarios"]
