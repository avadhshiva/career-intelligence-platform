"""Recruiter-readable resume routing explanations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from recommendation_engine import RecommendationResult
from resume_routing.scoring import rank_variants
from resume_routing.variants import RESUME_VARIANTS, ResumeVariant


@dataclass
class ResumeRouteResult:
    recommended_resume: str
    confidence: float
    why_selected: list[str] = field(default_factory=list)
    rejected_resume_reasons: dict[str, str] = field(default_factory=dict)
    role_alignment_breakdown: dict[str, float] = field(default_factory=dict)
    variant_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_resume": self.recommended_resume,
            "confidence": self.confidence,
            "why_selected": list(self.why_selected),
            "rejected_resume_reasons": dict(self.rejected_resume_reasons),
            "role_alignment_breakdown": dict(self.role_alignment_breakdown),
            "variant_id": self.variant_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResumeRouteResult":
        return cls(
            recommended_resume=str(data.get("recommended_resume") or ""),
            confidence=float(data.get("confidence") or 0.0),
            why_selected=list(data.get("why_selected") or []),
            rejected_resume_reasons=dict(data.get("rejected_resume_reasons") or {}),
            role_alignment_breakdown=dict(data.get("role_alignment_breakdown") or {}),
            variant_id=str(data.get("variant_id") or ""),
        )


def _why_lines(variant: ResumeVariant, rec: RecommendationResult, profile: CandidateProfile) -> list[str]:
    lines: list[str] = []
    detail = rec.match_detail or {}
    role_family = str(detail.get("primary_role_family") or "")

    if role_family in variant.suitable_role_families:
        lines.append(f"Strongest alignment with {variant.primary_focus} role expectations.")
    if detail.get("is_ai_transformation") and variant.variant_id in ("ai_transformation", "ai_enablement"):
        lines.append("Highest AI modernization and transformation evidence for this role.")
    if detail.get("is_release_governance_heavy") and variant.variant_id == "release_governance":
        lines.append("Highest governance overlap for release coordination responsibilities.")
    if detail.get("is_architecture_heavy") and variant.variant_id == "tpm":
        lines.append("Strongest architecture coordination and technical delivery narrative.")
    if profile.governance_experience >= 0.5 and variant.variant_id in ("release_governance", "program_leadership"):
        lines.append("Strong stakeholder and governance alignment documented on resume.")
    if profile.transformation_focus >= 0.5 and variant.variant_id == "ai_transformation":
        lines.append("Strongest transformation ownership signals for executive audiences.")

    for strength in variant.strengths[:2]:
        if strength not in lines:
            lines.append(strength)
    return lines[:3]


def _reject_reason(variant: ResumeVariant, score: float, best: ResumeVariant) -> str:
    if score < 0.25:
        return f"Limited overlap with {best.primary_focus} priorities for this role."
    if variant.variant_id in ("ai_transformation", "ai_enablement") and best.variant_id not in (
        "ai_transformation",
        "ai_enablement",
    ):
        return "AI-heavy positioning may over-index for a non-AI primary role."
    if variant.variant_id == "enterprise_delivery" and best.variant_id == "tpm":
        return "Delivery resume lacks technical program depth expected here."
    return f"Lower role-family proximity than {best.label}."


def route_resume(
    *,
    profile: CandidateProfile,
    rec: RecommendationResult,
    active_resume_label: str | None = None,
) -> ResumeRouteResult:
    ranked = rank_variants(profile=profile, rec=rec)
    best_variant, best_score = ranked[0]
    label = active_resume_label or best_variant.label
    if active_resume_label and best_score >= 0.55:
        label = active_resume_label

    rejected: dict[str, str] = {}
    breakdown: dict[str, float] = {}
    for variant, score in ranked:
        breakdown[variant.variant_id] = round(score, 3)
        if variant.variant_id != best_variant.variant_id:
            rejected[variant.label] = _reject_reason(variant, score, best_variant)

    confidence = round(min(0.95, 0.45 + best_score * 0.55), 3)
    return ResumeRouteResult(
        recommended_resume=label if active_resume_label else best_variant.label,
        confidence=confidence,
        why_selected=_why_lines(best_variant, rec, profile),
        rejected_resume_reasons=rejected,
        role_alignment_breakdown=breakdown,
        variant_id=best_variant.variant_id,
    )


def attach_routing_to_recommendation(
    *,
    profile: CandidateProfile,
    rec: RecommendationResult,
    active_resume_label: str | None = None,
) -> ResumeRouteResult:
    route = route_resume(profile=profile, rec=rec, active_resume_label=active_resume_label)
    detail = dict(rec.match_detail or {})
    detail["resume_routing"] = route.to_dict()
    detail["recommended_resume"] = route.recommended_resume
    rec.match_detail = detail
    return route


def routing_from_recommendation(rec: RecommendationResult) -> ResumeRouteResult | None:
    detail = rec.match_detail or {}
    cached = detail.get("resume_routing")
    if cached:
        return ResumeRouteResult.from_dict(cached)
    recommended = detail.get("recommended_resume")
    if recommended:
        return ResumeRouteResult(recommended_resume=str(recommended), confidence=0.5)
    return None
