"""Lightweight structured logging for operational stabilization (stdlib only)."""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Iterator

_OPS_LOGGER_NAME = "career_agent.ops"
_configured = False


def _format_fields(**fields: Any) -> str:
    parts: list[str] = []
    for key, value in sorted(fields.items()):
        if value is None:
            continue
        parts.append(f"{key}={value!r}")
    return " ".join(parts)


def get_ops_logger() -> logging.Logger:
    return logging.getLogger(_OPS_LOGGER_NAME)


def configure_ops_logging(level: int | None = None) -> None:
    """Idempotent handler setup for Streamlit and CLI runs."""
    global _configured
    try:
        from version import BUILD_INFO, __version__

        _startup_version = __version__
        _startup_release = BUILD_INFO.get("release", "")
    except Exception:
        _startup_version = "unknown"
        _startup_release = ""

    logger = get_ops_logger()
    if level is None:
        raw = (os.environ.get("CAREER_AGENT_LOG_LEVEL") or "INFO").strip().upper()
        level = getattr(logging, raw, logging.INFO)
    logger.setLevel(level)
    if not _configured:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"),
        )
        logger.addHandler(handler)
        logger.propagate = False
        _configured = True
        logger.info(
            "ops_logging_ready version=%s release=%s",
            _startup_version,
            _startup_release,
        )


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    configure_ops_logging()
    suffix = _format_fields(**fields)
    message = f"event={event}"
    if suffix:
        message = f"{message} {suffix}"
    get_ops_logger().log(level, message)


@contextmanager
def timed_operation(event: str, **fields: Any) -> Iterator[None]:
    """Log start/end with elapsed_ms (no external metrics stack)."""
    configure_ops_logging()
    log_event(f"{event}_start", **fields)
    started = time.perf_counter()
    try:
        yield
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        log_event(
            f"{event}_failed",
            level=logging.ERROR,
            elapsed_ms=elapsed_ms,
            error_type=type(exc).__name__,
            error=str(exc),
            **fields,
        )
        raise
    else:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        log_event(f"{event}_end", elapsed_ms=elapsed_ms, **fields)
