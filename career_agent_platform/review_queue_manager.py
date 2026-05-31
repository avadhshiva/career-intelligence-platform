"""Human review queue — persist approve / reject / archive / applied decisions."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from recommendation_engine import ApprovalStatus, RecommendationResult
from queue_validation import repair_queue_store, is_valid_queue_entry

DEMO_JOB_ID_PREFIXES: tuple[str, ...] = ("sample_", "tmp", "preview_")
DEMO_ORIGINS: frozenset[str] = frozenset({"preview", "demo", "sample"})


class QueueState(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    ARCHIVED = "archived"


_ALLOWED_TRANSITIONS: dict[QueueState, set[QueueState]] = {
    QueueState.PENDING_REVIEW: {
        QueueState.APPROVED,
        QueueState.REJECTED,
        QueueState.ARCHIVED,
    },
    QueueState.APPROVED: {QueueState.APPLIED, QueueState.ARCHIVED},
    QueueState.REJECTED: {QueueState.ARCHIVED},
    QueueState.APPLIED: {QueueState.ARCHIVED},
    QueueState.ARCHIVED: set(),
}


def _platform_root() -> Path:
    return Path(__file__).resolve().parent


@dataclass
class ReviewQueueEntry:
    """Single job in the human review queue."""

    entry_id: str
    job_id: str
    state: QueueState
    recommendation: dict[str, Any]
    reviewer_notes: str = ""
    rejection_reason: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "job_id": self.job_id,
            "state": self.state.value,
            "recommendation": self.recommendation,
            "reviewer_notes": self.reviewer_notes,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ReviewQueueManager:
    """JSON-backed review queue for Phase 5A human-in-the-loop workflow."""

    def __init__(self, data_dir: Path | None = None) -> None:
        root = data_dir or (_platform_root() / "applications" / "data")
        self._data_dir = root
        self._queue_path = root / "review_queue.json"

    def initialize(self) -> None:
        from demo_mode import persistence_writes_enabled

        self._data_dir.mkdir(parents=True, exist_ok=True)
        if not persistence_writes_enabled():
            return
        if not self._queue_path.exists():
            self._queue_path.write_text(
                json.dumps({"entries": []}, indent=2),
                encoding="utf-8",
            )
        from services.listing_urls import scrub_persisted_listing_urls

        scrub_persisted_listing_urls(self._data_dir)
        # Always self-heal queue persistence on startup (removes null/sparse/malformed rows).
        self._repair_persisted_queue()

    def _load(self) -> dict[str, Any]:
        self.initialize()
        raw = json.loads(self._queue_path.read_text(encoding="utf-8"))
        store, _report, changed = repair_queue_store(raw)
        if changed:
            self._save(store)
        return store

    def _save(self, data: dict[str, Any]) -> None:
        from demo_mode import persistence_writes_enabled

        if not persistence_writes_enabled():
            return
        self._queue_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _repair_persisted_queue(self) -> None:
        """Repair persisted queue JSON in-place (idempotent)."""
        try:
            raw = json.loads(self._queue_path.read_text(encoding="utf-8"))
        except Exception:
            raw = {"entries": []}
        store, _report, changed = repair_queue_store(raw)
        if changed:
            self._save(store)

    def _find_pending_entry_id(self, store: dict[str, Any], job_id: str) -> str | None:
        for entry in reversed(store.get("entries") or []):
            if not is_valid_queue_entry(entry):
                continue
            if entry["job_id"] == job_id and entry["state"] == QueueState.PENDING_REVIEW.value:
                return entry["entry_id"]
        return None

    @staticmethod
    def is_demo_entry(entry: dict[str, Any]) -> bool:
        origin = str(entry.get("origin") or "").lower()
        if origin in DEMO_ORIGINS:
            return True
        job_id = str(entry.get("job_id") or "")
        return any(job_id.startswith(prefix) for prefix in DEMO_JOB_ID_PREFIXES)

    @classmethod
    def filter_user_entries(cls, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [e for e in entries if not cls.is_demo_entry(e)]

    def purge_demo_entries(self) -> int:
        """Remove preview/sample rows from persisted queue (one-time hygiene)."""
        store = self._load()
        before = len(store.get("entries") or [])
        store["entries"] = [
            e for e in (store.get("entries") or []) if is_valid_queue_entry(e)
        ]
        removed = before - len(store["entries"])
        if removed:
            self._save(store)
        return removed

    def enqueue_recommendation(
        self,
        rec: RecommendationResult,
        *,
        origin: str = "user",
    ) -> str:
        store = self._load()
        existing = self._find_pending_entry_id(store, rec.job_id)
        if existing:
            return existing
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        payload = rec.to_dict()
        payload["approval_status"] = ApprovalStatus.PENDING.value
        store["entries"].append(
            {
                "entry_id": entry_id,
                "job_id": rec.job_id,
                "state": QueueState.PENDING_REVIEW.value,
                "origin": origin,
                "recommendation": payload,
                "reviewer_notes": "",
                "rejection_reason": "",
                "created_at": now,
                "updated_at": now,
            }
        )
        self._save(store)
        return entry_id

    def enqueue_many(
        self,
        recommendations: list[RecommendationResult],
        *,
        origin: str = "user",
    ) -> list[str]:
        return [self.enqueue_recommendation(r, origin=origin) for r in recommendations]

    @staticmethod
    def unique_entries_by_job(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep the latest queue row per job_id (avoids inflated preview counts)."""
        latest: dict[str, dict[str, Any]] = {}
        for entry in entries:
            # NOTE: This helper is intentionally tolerant because some callers/tests
            # pass minimal dicts (job_id + updated_at) that are not full persisted
            # queue rows yet.
            if not entry or not isinstance(entry, dict):
                continue
            job_id = entry.get("job_id")
            if not job_id:
                continue
            prev = latest.get(job_id)
            if prev is None or (entry.get("updated_at") or "") >= (prev.get("updated_at") or ""):
                latest[job_id] = entry
        return list(latest.values())

    def _find(self, store: dict[str, Any], entry_id: str) -> dict[str, Any]:
        for entry in store.get("entries") or []:
            if not is_valid_queue_entry(entry):
                continue
            if entry["entry_id"] == entry_id:
                return entry
        raise KeyError(f"entry_id not found: {entry_id}")

    def _transition(
        self,
        entry_id: str,
        new_state: QueueState,
        *,
        reviewer_notes: str = "",
        rejection_reason: str = "",
    ) -> dict[str, Any]:
        store = self._load()
        entry = self._find(store, entry_id)
        allowed = _ALLOWED_TRANSITIONS.get(QueueState(entry["state"]), set())
        if new_state not in allowed and new_state != QueueState(entry["state"]):
            raise ValueError(
                f"Invalid transition {entry['state']} -> {new_state.value}",
            )
        entry["state"] = new_state.value
        entry["reviewer_notes"] = reviewer_notes
        if rejection_reason:
            entry["rejection_reason"] = rejection_reason
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        rec = entry.get("recommendation") or {}
        if new_state == QueueState.APPROVED:
            rec["approval_status"] = ApprovalStatus.APPROVED.value
        elif new_state == QueueState.REJECTED:
            rec["approval_status"] = ApprovalStatus.REJECTED.value
            rec["rejection_reason"] = rejection_reason
        elif new_state == QueueState.ARCHIVED:
            rec["approval_status"] = ApprovalStatus.ARCHIVED.value
        entry["recommendation"] = rec
        self._save(store)
        return entry

    def approve(self, entry_id: str, notes: str = "") -> dict[str, Any]:
        return self._transition(entry_id, QueueState.APPROVED, reviewer_notes=notes)

    def reject(self, entry_id: str, reason: str = "", notes: str = "") -> dict[str, Any]:
        return self._transition(
            entry_id,
            QueueState.REJECTED,
            reviewer_notes=notes,
            rejection_reason=reason,
        )

    def mark_applied(self, entry_id: str, notes: str = "") -> dict[str, Any]:
        return self._transition(entry_id, QueueState.APPLIED, reviewer_notes=notes)

    def archive(self, entry_id: str, notes: str = "") -> dict[str, Any]:
        return self._transition(entry_id, QueueState.ARCHIVED, reviewer_notes=notes)

    def list_by_state(
        self,
        state: QueueState,
        *,
        include_demo: bool = False,
    ) -> list[dict[str, Any]]:
        store = self._load()
        rows = [
            e
            for e in (store.get("entries") or [])
            if is_valid_queue_entry(e) and e.get("state") == state.value
        ]
        if include_demo:
            return rows
        return self.filter_user_entries(rows)

    def list_pending(self, *, include_demo: bool = False) -> list[dict[str, Any]]:
        return self.list_by_state(QueueState.PENDING_REVIEW, include_demo=include_demo)

    def list_approved(self, *, include_demo: bool = False) -> list[dict[str, Any]]:
        return self.list_by_state(QueueState.APPROVED, include_demo=include_demo)

    def list_rejected(self, *, include_demo: bool = False) -> list[dict[str, Any]]:
        return self.list_by_state(QueueState.REJECTED, include_demo=include_demo)

    def list_applied(self, *, include_demo: bool = False) -> list[dict[str, Any]]:
        return self.list_by_state(QueueState.APPLIED, include_demo=include_demo)

    def list_archived(self, *, include_demo: bool = False) -> list[dict[str, Any]]:
        return self.list_by_state(QueueState.ARCHIVED, include_demo=include_demo)

    def get_entry(self, entry_id: str) -> dict[str, Any]:
        return self._find(self._load(), entry_id)
