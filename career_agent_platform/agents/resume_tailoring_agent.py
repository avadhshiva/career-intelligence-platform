"""Resume tailoring agent — prepares tailored resume variants after human approval.

Phase 5 placeholder: scaffolding only. Does not modify ontology scoring or
canonical_unified_pipeline behavior. Future: LLM-assisted tailoring with
deterministic explainability preserved for match replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TailoringRequest:
    job_id: str
    base_resume_text: str
    match_explainability: dict[str, Any] = field(default_factory=dict)
    emphasis_dimensions: list[str] = field(default_factory=list)


@dataclass
class TailoringResult:
    job_id: str
    status: str
    tailored_resume_text: str | None = None
    change_log: list[str] = field(default_factory=list)


class ResumeTailoringAgent:
    """Produces tailored resume drafts for approved jobs (stub implementation)."""

    def tailor(self, request: TailoringRequest) -> TailoringResult:
        """Return a placeholder result until LLM tailoring is implemented."""
        return TailoringResult(
            job_id=request.job_id,
            status="pending_implementation",
            tailored_resume_text=None,
            change_log=[
                "Phase 5: tailoring agent scaffold only.",
                "Deterministic match explainability must be preserved on replay.",
            ],
        )
