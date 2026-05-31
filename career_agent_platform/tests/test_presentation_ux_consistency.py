"""Presentation-layer UX consistency helpers."""

from __future__ import annotations

from presentation.explainability import lines_distinct_from_reference, strengths_distinct_from_summary
from presentation.labels import discourages_primary_approve
from review_queue_manager import ReviewQueueManager


def test_discourages_primary_approve_gated_and_limited() -> None:
    assert discourages_primary_approve(
        eligibility_passed=False,
        recommendation_priority="STRONG_MATCH",
    )
    assert discourages_primary_approve(
        eligibility_passed=True,
        recommendation_priority="LOW_MATCH",
    )
    assert discourages_primary_approve(
        eligibility_passed=True,
        recommendation_priority="BORDERLINE",
    )
    assert not discourages_primary_approve(
        eligibility_passed=True,
        recommendation_priority="STRONG_MATCH",
    )


def test_lines_distinct_from_reference_drops_driver_overlap() -> None:
    reference = [
        "Matrix stakeholder leadership reads clearly on the resume",
        "Governance evidence lighter than role expects",
    ]
    drivers = [
        "Matrix stakeholder leadership reads clearly on the resume",
        "Delivery themes track role-critical capabilities",
    ]
    out = lines_distinct_from_reference(reference, drivers)
    assert len(out) == 1
    assert "Delivery themes" in out[0]


def test_strengths_distinct_from_summary_drops_overlap() -> None:
    summary = "Strong TPM background with platform delivery."
    strengths = [
        "Strong TPM background with platform delivery",
        "Stakeholder alignment across eng and product",
    ]
    out = strengths_distinct_from_summary(summary, strengths)
    assert len(out) == 1
    assert "Stakeholder" in out[0]


def test_unique_entries_by_job_keeps_latest() -> None:
    entries = [
        {"job_id": "a", "updated_at": "2020-01-01T00:00:00+00:00", "state": "pending_review"},
        {"job_id": "a", "updated_at": "2021-01-01T00:00:00+00:00", "state": "approved"},
        {"job_id": "b", "updated_at": "2020-01-01T00:00:00+00:00", "state": "pending_review"},
    ]
    unique = ReviewQueueManager.unique_entries_by_job(entries)
    assert len(unique) == 2
    by_job = {e["job_id"]: e for e in unique}
    assert by_job["a"]["state"] == "approved"
