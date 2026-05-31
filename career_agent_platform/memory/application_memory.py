"""Application memory — durable store for reviews, applications, and outcomes.

Phase 5: JSON file store under applications/data/. No auto-apply.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _platform_root() -> Path:
    return Path(__file__).resolve().parents[1]


class ApplicationMemory:
    """Lightweight JSON persistence for human review and application state."""

    def __init__(self, data_dir: Path | None = None) -> None:
        root = data_dir or (_platform_root() / "applications" / "data")
        self._data_dir = root
        self._reviews_path = root / "reviews.json"
        self._applications_path = root / "applications.json"

    def initialize(self) -> None:
        """Create data directory and empty store files if missing."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        for path, default in (
            (self._reviews_path, {"reviews": []}),
            (self._applications_path, {"applications": []}),
        ):
            if not path.exists():
                path.write_text(json.dumps(default, indent=2), encoding="utf-8")

    def _load(self, path: Path) -> dict[str, Any]:
        self.initialize()
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def record_review_pending(
        self,
        job_id: str,
        match_score: float,
        explainability: dict[str, Any],
        notes: str = "",
    ) -> str:
        store = self._load(self._reviews_path)
        review_id = str(uuid.uuid4())
        store["reviews"].append(
            {
                "review_id": review_id,
                "job_id": job_id,
                "match_score": match_score,
                "explainability": explainability,
                "notes": notes,
                "status": "pending",
                "decision": None,
                "reviewer_notes": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._save(self._reviews_path, store)
        return review_id

    def record_review_decision(self, review_id: str, decision: str, reviewer_notes: str = "") -> dict[str, Any]:
        store = self._load(self._reviews_path)
        for entry in store["reviews"]:
            if entry["review_id"] == review_id:
                entry["status"] = "decided"
                entry["decision"] = decision
                entry["reviewer_notes"] = reviewer_notes
                entry["decided_at"] = datetime.now(timezone.utc).isoformat()
                self._save(self._reviews_path, store)
                return entry
        raise KeyError(f"review_id not found: {review_id}")
