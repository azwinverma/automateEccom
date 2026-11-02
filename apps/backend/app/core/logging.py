"""Structured JSON logging with request/trace/tenant context and secret redaction."""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

SENSITIVE_KEYS = re.compile(
    r"(pass(word)?|secret|token|authorization|api[_-]?key|cookie|otp|code_hash|recovery|private[_-]?key|card)",
    re.IGNORECASE,
)
REDACTED = "[REDACTED]"


def _redact(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return value
    if isinstance(value, dict):
        return {
            k: (REDACTED if isinstance(k, str) and SENSITIVE_KEYS.search(k) else _redact(v, depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact(v, depth + 1) for v in value]
    return value


def redact_processor(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return _redact(event_dict)


def configure_logging(level: str = "INFO", json: bool = True) -> None:
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact_processor,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: Any = structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=level.upper(), stream=sys.stdout, format="%(message)s")
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)
