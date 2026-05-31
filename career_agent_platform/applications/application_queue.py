"""Application queue — prioritized queue of jobs approved for tailoring/submission.

Phase 5: local JSON queue. Does not submit applications or drive browser automation.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class QueueStatus(str, Enum):
    QUEUED = "queued"
    TAILORING = "tailoring"
    READY = "ready"
    SUBMITTED = "submitted"
    WITHDRAWN = "withdrawn"


def _platform_root() -> Path:
    return Path(__file__).resolve().parents[1]


class ApplicationQueue:
    """FIFO-style application queue with persistent JSON backing store."""

    def __init__(self, data_dir: Path | None = None) -> None:
        root = data_dir or (_platform_root() / "applications" / "data")
        self._data_dir = root
        self._queue_path = root / "queue.json"

    def initialize(self) -> None:
        """Create queue storage (invoked by run_agent_platform.ps1 on startup)."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if not self._queue_path.exists():
            self._queue_path.write_text(
                json.dumps({"items": []}, indent=2),
                encoding="utf-8",
            )

    def _load(self) -> dict[str, Any]:
        self.initialize()
        return json.loads(self._queue_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self._queue_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def enqueue(self, job_id: str, priority: int = 0, metadata: dict[str, Any] | None = None) -> str:
        data = self._load()
        item_id = str(uuid.uuid4())
        data["items"].append(
            {
                "item_id": item_id,
                "job_id": job_id,
                "priority": priority,
                "status": QueueStatus.QUEUED.value,
                "metadata": metadata or {},
                "enqueued_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        data["items"].sort(key=lambda x: (-x["priority"], x["enqueued_at"]))
        self._save(data)
        return item_id

    def list_queued(self) -> list[dict[str, Any]]:
        data = self._load()
        return [i for i in data["items"] if i["status"] == QueueStatus.QUEUED.value]

    def update_status(self, item_id: str, status: QueueStatus) -> dict[str, Any]:
        data = self._load()
        for item in data["items"]:
            if item["item_id"] == item_id:
                item["status"] = status.value
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save(data)
                return item
        raise KeyError(f"item_id not found: {item_id}")
