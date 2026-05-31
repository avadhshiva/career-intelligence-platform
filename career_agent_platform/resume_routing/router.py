"""Resume routing facade."""

from __future__ import annotations

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from resume_routing.explanations import (
    ResumeRouteResult,
    attach_routing_to_recommendation,
    route_resume,
    routing_from_recommendation,
)
from resume_routing.scoring import rank_variants, score_variant
from resume_routing.variants import DEFAULT_VARIANT_ORDER, RESUME_VARIANTS, ResumeVariant

_FAMILY_TO_VARIANT: dict[str, str] = {
    "ai_transformation": "ai_transformation",
    "ai_program_management": "ai_enablement",
    "technical_program_management": "tpm",
    "release_governance": "release_governance",
    "enterprise_delivery": "enterprise_delivery",
    "program_leadership": "program_leadership",
    "cloud_transformation": "enterprise_delivery",
    "platform_modernization": "ai_enablement",
    "digital_transformation": "ai_transformation",
    "transformation_office": "ai_transformation",
}


def route_resume_for_family(profile: CandidateProfile, role_family: str) -> str:
    """Pick variant label for a role family without a full job recommendation."""
    variant_id = _FAMILY_TO_VARIANT.get(role_family, "enterprise_delivery")
    variant = RESUME_VARIANTS.get(variant_id)
    if variant is None:
        return profile.explanations.get("primary_career_track", {}).get("display", "Enterprise Delivery Resume")
    if profile.primary_career_track.value in variant.suitable_role_families:
        return variant.label
    return variant.label


__all__ = [
    "DEFAULT_VARIANT_ORDER",
    "RESUME_VARIANTS",
    "ResumeRouteResult",
    "ResumeVariant",
    "attach_routing_to_recommendation",
    "rank_variants",
    "route_resume",
    "routing_from_recommendation",
    "route_resume_for_family",
    "score_variant",
]
