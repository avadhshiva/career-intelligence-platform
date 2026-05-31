"""Centralized validation + repair for persisted review queue entries.

This module must be importable from both UI and persistence layers without
creating circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from presentation.sanitize import is_placeholder_text, sanitize_display_text


DEMO_JOB_ID_PREFIXES: tuple[str, ...] = ("sample_", "tmp", "preview_")
DEMO_ORIGINS: frozenset[str] = frozenset({"preview", "demo", "sample"})

VALID_QUEUE_STATES: frozenset[str] = frozenset(
    {"pending_review", "approved", "rejected", "applied", "archived"},
)

_BAD_LABELS = frozenset({"--", "role", "company", "role @ company"})


def _is_demo_entry(entry: dict[str, Any]) -> bool:
    origin = str(entry.get("origin") or "").lower().strip()
    if origin in DEMO_ORIGINS:
        return True
    job_id = str(entry.get("job_id") or "").lower().strip()
    return any(job_id.startswith(prefix) for prefix in DEMO_JOB_ID_PREFIXES)


def _valid_display_value(value: str | None) -> bool:
    if value is None:
        return False
    raw = str(value).strip()
    if is_placeholder_text(raw):
        return False
    cleaned = sanitize_display_text(raw)
    if not cleaned:
        return False
    low = cleaned.strip().lower()
    if low in _BAD_LABELS:
        return False
    if any(low.startswith(p) for p in DEMO_JOB_ID_PREFIXES):
        return False
    if "@" in low and low.replace(" ", "") == "role@company":
        return False
    return True


def is_valid_queue_entry(entry: Any) -> bool:
    """Strict validation for entries that may appear in UI or counts."""

    if not entry or not isinstance(entry, dict):
        return False
    if _is_demo_entry(entry):
        return False

    entry_id = str(entry.get("entry_id") or "").strip()
    if not entry_id:
        return False

    state = str(entry.get("state") or "").strip()
    if state not in VALID_QUEUE_STATES:
        return False

    rec = entry.get("recommendation")
    if not rec or not isinstance(rec, dict):
        return False

    job_id = str(entry.get("job_id") or rec.get("job_id") or "").strip()
    if not job_id or any(job_id.lower().startswith(p) for p in DEMO_JOB_ID_PREFIXES):
        return False

    title = rec.get("job_title")
    company = rec.get("company")
    if not _valid_display_value(str(title) if title is not None else None):
        return False
    if not _valid_display_value(str(company) if company is not None else None):
        return False

    # Ensure the rec looks like a real snapshot (avoid empty dicts).
    if not any(k in rec for k in ("overall_match", "match_detail", "why_matched", "why_not_matched")):
        return False

    return True


@dataclass(frozen=True)
class QueueRepairReport:
    removed_nulls: int = 0
    removed_malformed: int = 0
    removed_demo_or_placeholder: int = 0

    @property
    def total_removed(self) -> int:
        return self.removed_nulls + self.removed_malformed + self.removed_demo_or_placeholder


def repair_queue_entries(entries: Any) -> tuple[list[dict[str, Any]], QueueRepairReport]:
    """Repair a persisted queue entries list by removing invalid rows (including None)."""

    removed_nulls = 0
    removed_malformed = 0
    removed_demo_or_placeholder = 0

    if not isinstance(entries, list):
        return [], QueueRepairReport(removed_nulls=0, removed_malformed=1, removed_demo_or_placeholder=0)

    cleaned: list[dict[str, Any]] = []
    for raw in entries:
        if raw is None:
            removed_nulls += 1
            continue
        if not isinstance(raw, dict):
            removed_malformed += 1
            continue
        if not is_valid_queue_entry(raw):
            removed_demo_or_placeholder += 1
            continue
        cleaned.append(raw)

    return cleaned, QueueRepairReport(
        removed_nulls=removed_nulls,
        removed_malformed=removed_malformed,
        removed_demo_or_placeholder=removed_demo_or_placeholder,
    )


def repair_queue_store(store: Any) -> tuple[dict[str, Any], QueueRepairReport, bool]:
    """Repair the full JSON store shape: ensure dict with list 'entries'."""

    if not isinstance(store, dict):
        cleaned, report = repair_queue_entries([])
        return {"entries": cleaned}, report, True

    before_entries = store.get("entries")
    cleaned_entries, report = repair_queue_entries(before_entries)
    changed = report.total_removed > 0 or not isinstance(before_entries, list)
    out = dict(store)
    out["entries"] = cleaned_entries
    return out, report, changed

