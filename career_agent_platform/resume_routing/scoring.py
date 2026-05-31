"""Deterministic resume variant scoring."""

from __future__ import annotations

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from recommendation_engine import RecommendationResult
from resume_routing.variants import RESUME_VARIANTS, ResumeVariant


def _role_family(rec: RecommendationResult) -> str:
    detail = rec.match_detail or {}
    return str(detail.get("primary_role_family") or "enterprise_delivery")


def _dimension_overlap(profile: CandidateProfile, variant: ResumeVariant) -> float:
    vec = profile.capability_vector or {}
    focus_map = {
        "ai transformation": ("transformation", "strategy", "governance"),
        "ai enablement": ("automation", "platform", "delivery"),
        "technical program management": ("delivery", "architecture", "governance"),
        "release governance": ("governance", "delivery", "execution"),
        "enterprise delivery": ("delivery", "governance", "stakeholder"),
        "program leadership": ("governance", "strategy", "stakeholder"),
    }
    keys = focus_map.get(variant.primary_focus, ("delivery", "governance"))
    hits = [float(vec.get(k, 0.0)) for k in keys if k in vec]
    if not hits:
        return 0.35
    return min(1.0, sum(hits) / len(hits))


def score_variant(
    *,
    profile: CandidateProfile,
    rec: RecommendationResult,
    variant: ResumeVariant,
) -> float:
    role_family = _role_family(rec)
    score = 0.0

    if role_family in variant.suitable_role_families:
        score += 0.45
    elif role_family in variant.unsuitable_role_families:
        score -= 0.35

    score += _dimension_overlap(profile, variant) * 0.25

    detail = rec.match_detail or {}
    if detail.get("is_ai_transformation") and variant.variant_id in ("ai_transformation", "ai_enablement"):
        score += 0.15
    if detail.get("is_release_governance_heavy") and variant.variant_id == "release_governance":
        score += 0.18
    if detail.get("is_architecture_heavy") and variant.variant_id == "tpm":
        score += 0.12
    if detail.get("is_product_heavy") and variant.variant_id in ("enterprise_delivery", "program_leadership"):
        score += 0.08
    if detail.get("is_operations_heavy") and variant.variant_id == "enterprise_delivery":
        score += 0.10

    ai = (profile.ai_maturity.value if profile.ai_maturity else "none").lower()
    if ai in {"none", "awareness"} and variant.variant_id in ("ai_transformation", "ai_enablement"):
        score -= 0.20
    if ai in {"practitioner", "transformation_lead"} and variant.variant_id in ("ai_transformation", "ai_enablement"):
        score += 0.12

    if profile.transformation_focus >= 0.55 and variant.variant_id == "ai_transformation":
        score += 0.10
    if profile.governance_experience >= 0.55 and variant.variant_id in ("release_governance", "program_leadership"):
        score += 0.10

    primary = profile.primary_career_track.value
    if primary in variant.suitable_role_families:
        score += 0.12

    return max(0.0, min(1.0, score))


def rank_variants(
    *,
    profile: CandidateProfile,
    rec: RecommendationResult,
) -> list[tuple[ResumeVariant, float]]:
    ranked = [
        (variant, score_variant(profile=profile, rec=rec, variant=variant))
        for variant in RESUME_VARIANTS.values()
    ]
    return sorted(ranked, key=lambda item: (-item[1], item[0].variant_id))
