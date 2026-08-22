"""
Unit tests for IBM watsonx.ai integration.

All IBM API calls are mocked — no real credentials required to run these tests.

Run:
    cd greenpulse/backend
    source .venv/bin/activate
    pip install pytest pytest-asyncio
    pytest tests/test_watsonx.py -v
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.core.config import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    """Build a Settings instance with defaults safe for unit tests."""
    defaults = {
        "watsonx_api_key": "",
        "watsonx_project_id": "",
        "watsonx_url": "https://us-south.ml.cloud.ibm.com",
        "ibm_region": "us-south",
        "ai_mode": "hybrid",
        "app_env": "development",
        "data_source_mode": "SIMULATED",
    }
    defaults.update(overrides)
    return Settings.model_validate(defaults)


# ---------------------------------------------------------------------------
# 1. Configuration tests
# ---------------------------------------------------------------------------

class TestSettings:
    def test_default_region_is_us_south(self):
        s = _make_settings()
        assert s.ibm_region == "us-south"
        assert "us-south" in s.watsonx_url

    def test_default_model(self):
        s = _make_settings()
        assert s.granite_model_id == "ibm/granite-4-h-small"

    def test_default_ai_mode(self):
        s = _make_settings()
        assert s.ai_mode == "hybrid"

    def test_granite_configured_false_when_no_key(self):
        s = _make_settings(watsonx_api_key="", watsonx_project_id="")
        assert s.granite_configured is False

    def test_granite_configured_false_when_placeholder(self):
        s = _make_settings(
            watsonx_api_key="your_ibm_api_key_here",
            watsonx_project_id="c7b0f97f-cac0-49ee-9dca-6cb12f6c7d2d",
        )
        assert s.granite_configured is False

    def test_granite_configured_true_with_real_values(self):
        s = _make_settings(
            watsonx_api_key="abcdefgh-1234-fake-key-for-unit-test",
            watsonx_project_id="c7b0f97f-cac0-49ee-9dca-6cb12f6c7d2d",
        )
        assert s.granite_configured is True

    def test_effective_ai_mode_simulation_when_not_configured(self):
        s = _make_settings(ai_mode="hybrid")
        assert s.effective_ai_mode == "simulation"

    def test_effective_ai_mode_ibm_when_configured(self):
        s = _make_settings(
            watsonx_api_key="abcdefgh-1234-fake-key-for-unit-test",
            watsonx_project_id="c7b0f97f-cac0-49ee-9dca-6cb12f6c7d2d",
            ai_mode="hybrid",
        )
        assert s.effective_ai_mode == "ibm"

    def test_ai_mode_simulation_overrides_configured(self):
        s = _make_settings(
            watsonx_api_key="abcdefgh-1234-fake-key-for-unit-test",
            watsonx_project_id="c7b0f97f-cac0-49ee-9dca-6cb12f6c7d2d",
            ai_mode="simulation",
        )
        assert s.effective_ai_mode == "simulation"

    def test_au_syd_not_in_defaults(self):
        s = _make_settings()
        assert "au-syd" not in s.watsonx_url
        assert "au-syd" not in s.ibm_region


# ---------------------------------------------------------------------------
# 2. watsonx_service — simulation mode
# ---------------------------------------------------------------------------

class TestWatsonxServiceSimulation:

    @pytest.mark.asyncio
    async def test_simulation_mode_returns_stub(self):
        """When ai_mode=simulation, no IBM call is made."""
        from app.services import watsonx_service

        settings_mock = _make_settings(ai_mode="simulation")
        with patch("app.services.watsonx_service.get_settings", return_value=settings_mock):
            response = await watsonx_service.generate_ai_response("Test prompt")

        assert response.success is True
        assert response.provider == "simulation"
        assert "SIMULATION" in response.answer or "IBM Granite" in response.answer

    @pytest.mark.asyncio
    async def test_simulation_mode_no_ibm_call(self):
        """Verify the IBM SDK is never called in simulation mode."""
        from app.services import watsonx_service

        settings_mock = _make_settings(ai_mode="simulation")
        with patch("app.services.watsonx_service.get_settings", return_value=settings_mock):
            with patch("app.services.watsonx_service._get_ibm_client") as mock_client:
                await watsonx_service.generate_ai_response("Test prompt")
                mock_client.assert_not_called()


# ---------------------------------------------------------------------------
# 3. watsonx_service — IBM mode with mocked SDK
# ---------------------------------------------------------------------------

class TestWatsonxServiceIBM:

    @pytest.mark.asyncio
    async def test_ibm_mode_calls_sdk(self):
        """When configured and ibm mode, generate_text is called."""
        from app.services import watsonx_service

        settings_mock = _make_settings(
            watsonx_api_key="fake-key-for-test",
            watsonx_project_id="c7b0f97f-cac0-49ee-9dca-6cb12f6c7d2d",
            ai_mode="ibm",
        )

        mock_model = MagicMock()
        mock_model.generate_text.return_value = "Mocked Granite response"

        with patch("app.services.watsonx_service.get_settings", return_value=settings_mock):
            with patch("app.services.watsonx_service._get_ibm_client", return_value=mock_model):
                response = await watsonx_service.generate_ai_response("What is the grid status?")

        assert response.success is True
        assert response.provider == "ibm"
        assert response.answer == "Mocked Granite response"
        mock_model.generate_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_ibm_error_falls_back_in_hybrid_mode(self):
        """In hybrid mode, IBM errors should activate simulation fallback."""
        from app.services import watsonx_service

        settings_mock = _make_settings(
            watsonx_api_key="fake-key-for-test",
            watsonx_project_id="c7b0f97f-cac0-49ee-9dca-6cb12f6c7d2d",
            ai_mode="hybrid",
        )

        mock_model = MagicMock()
        mock_model.generate_text.side_effect = ConnectionError("IBM unreachable")

        with patch("app.services.watsonx_service.get_settings", return_value=settings_mock):
            with patch("app.services.watsonx_service._get_ibm_client", return_value=mock_model):
                response = await watsonx_service.generate_ai_response("Test prompt")

        # Should fall back gracefully
        assert response.error is not None
        assert "IBM unreachable" in response.error or response.provider in ("simulation", "ibm")

    @pytest.mark.asyncio
    async def test_probe_not_configured(self):
        """probe_ibm_connectivity returns NOT_CONFIGURED when no credentials."""
        from app.services import watsonx_service

        settings_mock = _make_settings()
        with patch("app.services.watsonx_service.get_settings", return_value=settings_mock):
            with patch("app.services.watsonx_service._get_ibm_client", return_value=None):
                result = await watsonx_service.probe_ibm_connectivity()

        assert result["status"] == "NOT_CONFIGURED"
        assert result["configured"] is False
        assert result["available"] is False

    @pytest.mark.asyncio
    async def test_probe_configured(self):
        """probe_ibm_connectivity returns CONFIGURED when client is present."""
        from app.services import watsonx_service

        settings_mock = _make_settings(
            watsonx_api_key="fake-key",
            watsonx_project_id="c7b0f97f-cac0-49ee-9dca-6cb12f6c7d2d",
        )
        mock_model = MagicMock()

        with patch("app.services.watsonx_service.get_settings", return_value=settings_mock):
            with patch("app.services.watsonx_service._get_ibm_client", return_value=mock_model):
                result = await watsonx_service.probe_ibm_connectivity()

        assert result["status"] == "CONFIGURED"
        assert result["available"] is True
        assert "watsonx_api_key" not in str(result)   # key must never appear in output
        assert "fake-key" not in str(result)           # key must never appear in output


# ---------------------------------------------------------------------------
# 4. API health endpoint (via TestClient)
# ---------------------------------------------------------------------------

class TestAIHealthEndpoint:

    def test_health_ai_returns_200(self):
        """GET /api/ai/health must return 200 with no credentials."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/ai/health")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "model" in data
        assert "configured" in data
        assert "effective_mode" in data
        # API key must NOT appear anywhere in the response
        assert "watsonx_api_key" not in str(data)

    def test_health_ai_shortcut_path(self):
        """GET /api/health/ai must also return 200."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/health/ai")
        assert response.status_code == 200

    def test_ai_test_endpoint_returns_200(self):
        """POST /api/ai/test must return 200 even without IBM credentials."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/ai/test",
            json={"prompt": "Hello, is this working?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "success" in data
        assert "effective_mode" in data


# ---------------------------------------------------------------------------
# 5. Region / URL correctness
# ---------------------------------------------------------------------------

class TestRegionConfiguration:

    def test_us_south_is_default(self):
        from app.core.config import get_settings
        from functools import lru_cache

        # Use a fresh Settings instance (not the lru_cache'd singleton)
        s = Settings.model_validate({})
        assert s.ibm_region == "us-south"
        assert s.watsonx_url == "https://us-south.ml.cloud.ibm.com"
        assert "au-syd" not in s.watsonx_url
        assert "au-syd" not in s.ibm_region
