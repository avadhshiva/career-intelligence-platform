"""Regression tests for queue hydration / persistence integrity."""

from __future__ import annotations

import json
from pathlib import Path

from review_queue_manager import ReviewQueueManager


def test_review_queue_self_heals_null_and_sparse_entries(tmp_path: Path) -> None:
    path = tmp_path / "review_queue.json"
    # Include null, non-dict, missing keys, and one valid-ish minimal entry.
    path.write_text(
        json.dumps(
            {
                "entries": [
                    None,
                    "bad",
                    {"entry_id": "", "job_id": "x", "state": "pending_review", "recommendation": {}},
                    {
                        "entry_id": "e1",
                        "job_id": "job_1",
                        "state": "pending_review",
                        "origin": "user",
                        "recommendation": {
                            "job_id": "job_1",
                            "job_title": "Senior Technical Program Manager",
                            "company": "Contoso",
                            "overall_match": 0.7,
                            "match_detail": {},
                        },
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    mgr = ReviewQueueManager(data_dir=tmp_path)
    mgr.initialize()

    # Load should not crash and should rewrite invalid rows away.
    pending = mgr.list_pending(include_demo=True)
    assert len(pending) == 1
    assert pending[0]["entry_id"] == "e1"

    repaired = json.loads(path.read_text(encoding="utf-8"))
    assert repaired["entries"] and len(repaired["entries"]) == 1
    assert repaired["entries"][0]["entry_id"] == "e1"


def test_review_queue_drops_demo_entries_on_load(tmp_path: Path) -> None:
    path = tmp_path / "review_queue.json"
    path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "entry_id": "demo1",
                        "job_id": "sample_001",
                        "state": "pending_review",
                        "origin": "sample",
                        "recommendation": {
                            "job_id": "sample_001",
                            "job_title": "TPM",
                            "company": "ExampleCo",
                            "overall_match": 0.5,
                            "match_detail": {},
                        },
                    },
                    {
                        "entry_id": "u1",
                        "job_id": "job_123",
                        "state": "approved",
                        "origin": "user",
                        "recommendation": {
                            "job_id": "job_123",
                            "job_title": "Technical Program Manager",
                            "company": "RealCo",
                            "overall_match": 0.8,
                            "match_detail": {},
                        },
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    mgr = ReviewQueueManager(data_dir=tmp_path)
    mgr.initialize()

    assert len(mgr.list_pending(include_demo=True)) == 0
    assert len(mgr.list_approved()) == 1
    assert mgr.list_approved()[0]["entry_id"] == "u1"

