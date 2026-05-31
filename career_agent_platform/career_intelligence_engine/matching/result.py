"""Match result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobMatchResult:
    overall_match_score: float
    confidence: float
    capability_similarity: float
    eligibility_fit: float
    seniority_fit: float
    transformation_fit: float
    architecture_fit: float
    governance_fit: float
    risk_penalties: list[str] = field(default_factory=list)
    fit_summary: str = ""
    risks: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    dominant_match_dimensions: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    recommended_resume_improvements: list[str] = field(default_factory=list)
    gate_passed: bool = True
    gate_reasons: list[str] = field(default_factory=list)
    scorer_path: str = "deterministic_job_match_v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_match_score": self.overall_match_score,
            "confidence": self.confidence,
            "capability_similarity": self.capability_similarity,
            "eligibility_fit": self.eligibility_fit,
            "seniority_fit": self.seniority_fit,
            "transformation_fit": self.transformation_fit,
            "architecture_fit": self.architecture_fit,
            "governance_fit": self.governance_fit,
            "risk_penalties": list(self.risk_penalties),
            "fit_summary": self.fit_summary,
            "risks": list(self.risks),
            "missing_capabilities": list(self.missing_capabilities),
            "dominant_match_dimensions": list(self.dominant_match_dimensions),
            "strengths": list(self.strengths),
            "gaps": list(self.gaps),
            "recommended_resume_improvements": list(self.recommended_resume_improvements),
            "gate_passed": self.gate_passed,
            "gate_reasons": list(self.gate_reasons),
            "scorer_path": self.scorer_path,
        }
