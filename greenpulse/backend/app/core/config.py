from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # -------------------------------------------------------------------------
    # IBM watsonx.ai credentials
    # Set via environment variables — never hard-coded.
    #   WATSONX_API_KEY       — IBM Cloud IAM API key
    #   WATSONX_PROJECT_ID    — watsonx.ai project ID
    #   WATSONX_URL           — regional endpoint
    #   IBM_REGION            — region label (informational)
    #   WATSONX_MODEL_ID      — Granite model ID (GRANITE_MODEL_ID also accepted)
    # -------------------------------------------------------------------------
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    ibm_region: str = "us-south"

    # Accepts WATSONX_MODEL_ID or GRANITE_MODEL_ID (legacy) from environment.
    granite_model_id: str = Field(
        default="ibm/granite-4-h-small",
        validation_alias=AliasChoices("watsonx_model_id", "granite_model_id"),
    )

    # -------------------------------------------------------------------------
    # AI execution mode
    #   ibm        — always call IBM Granite (fail loudly if unavailable)
    #   simulation — deterministic local stub (no IBM call, good for dev)
    #   hybrid     — IBM Granite when configured, simulation fallback otherwise
    # -------------------------------------------------------------------------
    ai_mode: Literal["ibm", "simulation", "hybrid"] = "hybrid"

    # -------------------------------------------------------------------------
    # Weather / external APIs
    # -------------------------------------------------------------------------
    weather_api_key: str = ""

    # -------------------------------------------------------------------------
    # Database (not active in Milestone 1 — in-memory simulation only)
    # -------------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://greenpulse:greenpulse@localhost:5432/greenpulse"

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_secret_key: str = "change_this_in_production"
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    data_source_mode: Literal["LIVE", "SIMULATED", "HISTORICAL"] = "SIMULATED"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:5175"

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------
    @property
    def granite_configured(self) -> bool:
        """True only when real, non-placeholder credentials are present."""
        _placeholders = {
            "", "your_ibm_api_key_here", "YOUR_REAL_API_KEY_HERE",
            "REPLACE_WITH_YOUR_NEW_ROTATED_API_KEY",
            "REPLACE_WITH_YOUR_PROJECT_ID",
        }
        return (
            bool(self.watsonx_api_key)
            and bool(self.watsonx_project_id)
            and self.watsonx_api_key not in _placeholders
            and self.watsonx_project_id not in _placeholders
            and "REPLACE" not in self.watsonx_api_key
            and "YOUR_" not in self.watsonx_api_key
        )

    @property
    def effective_ai_mode(self) -> str:
        """Resolve the runtime AI mode.

        - 'ibm'        → IBM Granite always
        - 'simulation' → local stub always
        - 'hybrid'     → IBM when configured, simulation otherwise
        """
        if self.ai_mode == "ibm":
            return "ibm"
        if self.ai_mode == "simulation":
            return "simulation"
        # hybrid
        return "ibm" if self.granite_configured else "simulation"


@lru_cache
def get_settings() -> Settings:
    return Settings()
