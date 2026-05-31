"""Human-in-the-loop review agent — gates recommendations before tailoring.

Phase 5 placeholder: records approve/reject/defer decisions in application memory.
Does not auto-apply or submit applications.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from memory.application_memory import ApplicationMemory


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"


@dataclass
class ReviewRequest:
    job_id: str
    match_score: float
    explainability: dict[str, Any]
    notes: str = ""


@dataclass
class ReviewResult:
    job_id: str
    decision: ReviewDecision
    reviewer_notes: str = ""


class HumanReviewAgent:
    """Queues match results for human review and persists decisions."""

    def __init__(self, memory: ApplicationMemory | None = None) -> None:
        self._memory = memory or ApplicationMemory()

    def submit_for_review(self, request: ReviewRequest) -> str:
        """Enqueue a job match for human review; returns review queue id."""
        return self._memory.record_review_pending(
            job_id=request.job_id,
            match_score=request.match_score,
            explainability=request.explainability,
            notes=request.notes,
        )

    def record_decision(self, review_id: str, decision: ReviewDecision, notes: str = "") -> ReviewResult:
        """Persist a human decision (called from UI or external workflow)."""
        entry = self._memory.record_review_decision(review_id, decision.value, notes)
        return ReviewResult(
            job_id=entry["job_id"],
            decision=ReviewDecision(entry["decision"]),
            reviewer_notes=entry.get("reviewer_notes", ""),
        )
