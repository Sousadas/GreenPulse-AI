"""Structured event logger for GreenPulse observability."""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

import structlog

from app.core.config import get_settings


def _configure_structlog() -> None:
    log_level = getattr(logging, get_settings().log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


_configured = False


def get_logger(name: str = "greenpulse") -> structlog.BoundLogger:
    global _configured
    if not _configured:
        _configure_structlog()
        _configured = True
    return structlog.get_logger(name)


def log_event(
    event: str,
    *,
    category: str = "system",
    agent: str | None = None,
    tool: str | None = None,
    asset_id: str | None = None,
    duration_ms: float | None = None,
    data_source: str | None = None,
    model: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a structured observability event."""
    logger = get_logger()
    payload: dict[str, Any] = {
        "category": category,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if agent:
        payload["agent"] = agent
    if tool:
        payload["tool"] = tool
    if asset_id:
        payload["asset_id"] = asset_id
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 2)
    if data_source:
        payload["data_source"] = data_source
    if model:
        payload["model"] = model
    if extra:
        payload.update(extra)
    logger.info(event, **payload)
