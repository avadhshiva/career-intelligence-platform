"""Read-only demo mode for reviewer-safe exploration (no persistence writes)."""

from __future__ import annotations

import os

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def is_demo_mode() -> bool:
    """True when CAREER_AGENT_DEMO_MODE is set to a truthy value."""
    return os.environ.get("CAREER_AGENT_DEMO_MODE", "").strip().lower() in _TRUTHY


def persistence_writes_enabled() -> bool:
    """False in demo mode — blocks review queue, resumes, and application packages."""
    return not is_demo_mode()
