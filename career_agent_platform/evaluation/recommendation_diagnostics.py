"""Governance diagnostics layered on existing match results (no ranking changes)."""

from __future__ import annotations

from typing import Any

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.matching.result import JobMatchResult
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES


def _role_cluster_label(family_id: RoleFamilyId | str) -> str:
    if isinstance(family_id, RoleFamilyId):
        fid = family_id
    else:
        try:
            fid = RoleFamilyId(str(family_id))
        except ValueError:
            return str(family_id)
    meta = ROLE_FAMILIES.get(fid)
    return meta.display_name if meta else fid.value


def build_recommendation_diagnostics(
    profile: CandidateProfile,
    job: JobProfile,
    match: JobMatchResult,
) -> dict[str, Any]:
    """JSON-safe explainability metadata for logs, snapshots, and UI expanders."""
    primary = job.primary_role_family
    adjacent = list(profile.adjacent_role_families or [])
    adjacent_values = {a.value for a in adjacent}

    job_cluster = _role_cluster_label(primary)
    candidate_primary = profile.primary_career_track.value
    candidate_cluster = _role_cluster_label(profile.primary_career_track)

    is_primary_match = primary == profile.primary_career_track
    is_adjacent_match = primary.value in adjacent_values

    adjacency_reasons: list[str] = []
    if is_primary_match:
        adjacency_reasons.append(
            f"Job family {primary.value} matches candidate primary track.",
        )
    elif is_adjacent_match:
        adjacency_reasons.append(
            f"Job family {primary.value} is in candidate adjacent families.",
        )
    else:
        adjacency_reasons.append(
            f"Job family {primary.value} is outside primary/adjacent sets "
            f"(primary={candidate_primary}, adjacent={sorted(adjacent_values)}).",
        )

    top_dimensions = list(match.dominant_match_dimensions or [])[:6]
    missing_dimensions = [
        d for d in (match.gaps or [])[:6]
    ]

    return {
        "role_cluster": job_cluster,
        "candidate_primary_track": candidate_primary,
        "candidate_cluster": candidate_cluster,
        "job_primary_family": primary.value,
        "matched_role_clusters": [job_cluster],
        "top_matching_dimensions": top_dimensions,
        "missing_dimensions": missing_dimensions,
        "missing_capabilities": list(match.missing_capabilities or [])[:8],
        "adjacency": {
            "is_primary_match": is_primary_match,
            "is_adjacent_match": is_adjacent_match,
            "candidate_adjacent_families": sorted(adjacent_values),
            "reasoning": adjacency_reasons,
        },
        "fit_lenses": dict(match.to_dict().get("fit_lenses") or {}),
        "gate_passed": match.gate_passed,
        "gate_reasons": list(match.gate_reasons or [])[:6],
    }
