"""Deterministic capability gap analysis against a target role family."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.capability_vectors import (
    CAPABILITY_DIMENSIONS,
    DIMENSION_LABELS,
    get_role_family_vector,
)
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES

_WEAK_THRESHOLD = 0.35
_MISSING_THRESHOLD = 0.12
_STRONG_TARGET = 0.55


@dataclass
class GapAnalysisResult:
    target_family: str
    target_display_name: str
    missing_dimensions: list[str] = field(default_factory=list)
    weak_dimensions: list[str] = field(default_factory=list)
    suggested_evidence: list[str] = field(default_factory=list)
    resume_strengthening: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_family": self.target_family,
            "target_display_name": self.target_display_name,
            "missing_dimensions": list(self.missing_dimensions),
            "weak_dimensions": list(self.weak_dimensions),
            "suggested_evidence": list(self.suggested_evidence),
            "resume_strengthening": list(self.resume_strengthening),
        }


_DIMENSION_EVIDENCE_HINTS: dict[str, str] = {
    "ai_strategy": "AI strategy ownership, GenAI portfolio, or enterprise AI operating model",
    "transformation_strategy": "transformation roadmap and operating-model redesign",
    "executive_communication": "executive steering, board reporting, or C-suite sponsorship",
    "enterprise_governance": "governance frameworks, steering committees, or compliance oversight",
    "technical_execution": "hands-on technical delivery or engineering coordination",
    "delivery_execution": "program delivery outcomes and milestone ownership",
    "portfolio_management": "portfolio governance and benefits realization",
    "change_management": "organizational change and adoption metrics",
    "architecture_coordination": "architecture review boards and technical alignment",
    "release_governance": "release train, SDLC, or release governance",
    "product_thinking": "product roadmap ownership and customer outcomes",
    "operational_management": "run-state operations and service management",
    "engineering_depth": "engineering depth, code review, or platform build",
    "stakeholder_complexity": "matrix stakeholder management across business units",
    "organizational_leadership": "org design, team leadership, or workforce planning",
}


def analyze_capability_gaps(
    candidate_vector: dict[str, float],
    target_family: RoleFamilyId,
) -> GapAnalysisResult:
    """
    Compare candidate capability vector to target role-family vector.
    Fully deterministic and ontology-driven.
    """
    target_vec = get_role_family_vector(target_family)
    display = ROLE_FAMILIES[target_family].display_name

    missing: list[str] = []
    weak: list[str] = []
    evidence: list[str] = []
    strengthening: list[str] = []

    gaps: list[tuple[str, float, float]] = []
    for dim in CAPABILITY_DIMENSIONS:
        target_weight = float(target_vec.get(dim, 0.0))
        if target_weight < _MISSING_THRESHOLD:
            continue
        candidate_val = float(candidate_vector.get(dim, 0.0))
        gap = target_weight - candidate_val
        if gap > _MISSING_THRESHOLD:
            gaps.append((dim, gap, target_weight))

    gaps.sort(key=lambda x: (-x[1], x[0]))

    for dim, gap, target_weight in gaps[:8]:
        label = DIMENSION_LABELS.get(dim, dim.replace("_", " ").title())
        candidate_val = float(candidate_vector.get(dim, 0.0))
        if candidate_val < _MISSING_THRESHOLD:
            missing.append(label)
        elif candidate_val < _WEAK_THRESHOLD and target_weight >= _STRONG_TARGET:
            weak.append(label)

        hint = _DIMENSION_EVIDENCE_HINTS.get(dim)
        if hint and len(evidence) < 5:
            evidence.append(f"Add evidence of {hint}.")

    if missing or weak:
        top_dim = gaps[0][0] if gaps else ""
        hint = _DIMENSION_EVIDENCE_HINTS.get(top_dim, "role-specific capability evidence")
        strengthening.append(
            f"Add {hint} to improve {display} alignment."
        )

    priority_dims = [d for d, _, _ in gaps[:3]]
    if "ai_strategy" in priority_dims or "transformation_strategy" in priority_dims:
        strengthening.append(
            "Add AI strategy ownership and executive communication evidence "
            f"to improve {display} alignment."
        )

    return GapAnalysisResult(
        target_family=target_family.value,
        target_display_name=display,
        missing_dimensions=missing,
        weak_dimensions=weak,
        suggested_evidence=evidence[:5],
        resume_strengthening=strengthening[:4],
    )
