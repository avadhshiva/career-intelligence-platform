"""Capability-aware role-family distance (intelligence layer, deterministic)."""

from __future__ import annotations

from career_intelligence_engine.intelligence.capability_inference import infer_capabilities
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.ontology import (
    EnterpriseExposure,
    LeadershipLevel,
    RoleFamilyId,
    SeniorityLevel,
)
from career_intelligence_engine.intelligence.semantic_distance import compute_family_distance
from career_intelligence_engine.ontology.capability_graph import normalize_skills
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES, get_role_family

_SENIORITY_INDEX = {
    SeniorityLevel.INTERN: 0,
    SeniorityLevel.JUNIOR: 1,
    SeniorityLevel.MID: 2,
    SeniorityLevel.SENIOR: 3,
    SeniorityLevel.LEAD: 4,
    SeniorityLevel.PRINCIPAL: 5,
    SeniorityLevel.DIRECTOR: 6,
    SeniorityLevel.VP: 7,
    SeniorityLevel.C_LEVEL: 8,
    SeniorityLevel.UNKNOWN: 3,
}

_LEADERSHIP_INDEX = {
    LeadershipLevel.INDIVIDUAL_CONTRIBUTOR: 0,
    LeadershipLevel.TEAM_LEAD: 1,
    LeadershipLevel.PEOPLE_MANAGER: 2,
    LeadershipLevel.ORG_LEADER: 3,
    LeadershipLevel.EXECUTIVE: 4,
    LeadershipLevel.UNKNOWN: 1,
}

_ENTERPRISE_INDEX = {
    EnterpriseExposure.NONE: 0.0,
    EnterpriseExposure.LIMITED: 0.25,
    EnterpriseExposure.MODERATE: 0.5,
    EnterpriseExposure.STRONG: 0.75,
    EnterpriseExposure.DEEP: 1.0,
}

_WEIGHTS = {
    "capability": 0.30,
    "leadership": 0.15,
    "transformation": 0.15,
    "enterprise": 0.15,
    "domain": 0.15,
    "seniority": 0.10,
}


def _resolve_role_family(role_family: RoleFamilyId | str) -> RoleFamilyId:
    if isinstance(role_family, RoleFamilyId):
        return role_family
    return RoleFamilyId(role_family)


def _candidate_leadership_score(profile: CandidateProfile) -> float:
    base = _LEADERSHIP_INDEX.get(profile.leadership_level, 1) / 4.0
    governance_boost = profile.governance_experience * 0.15
    stakeholder_boost = profile.stakeholder_complexity * 0.1
    return round(min(1.0, base + governance_boost + stakeholder_boost), 3)


def _capability_overlap(
    capability_scores: dict[str, dict],
    primary_caps: list[str],
    secondary_caps: list[str],
) -> tuple[float, list[str]]:
    if not primary_caps and not secondary_caps:
        return 0.5, []

    primary_hits = 0.0
    secondary_hits = 0.0
    evidence: list[str] = []

    for cap_id in primary_caps:
        entry = capability_scores.get(cap_id)
        if entry and entry.get("score", 0) > 0:
            primary_hits += entry["score"]
            evidence.extend(entry.get("evidence", [])[:2])

    for cap_id in secondary_caps:
        entry = capability_scores.get(cap_id)
        if entry and entry.get("score", 0) > 0:
            secondary_hits += entry["score"] * 0.5
            evidence.extend(entry.get("evidence", [])[:1])

    primary_denom = max(len(primary_caps), 1)
    if secondary_caps:
        secondary_denom = max(len(secondary_caps), 1)
        overlap = min(1.0, (primary_hits / primary_denom + secondary_hits / secondary_denom) / 1.5)
    else:
        overlap = min(1.0, primary_hits / primary_denom)
    return round(overlap, 3), sorted(set(evidence))[:6]


def _domain_overlap(profile: CandidateProfile, role_family_id: RoleFamilyId) -> float:
    role_def = ROLE_FAMILIES[role_family_id]
    role_terms = {
        t.lower()
        for t in role_def.title_signals
        + role_def.experience_signals
        + role_def.skill_signals
    }
    candidate_domains = {d.lower() for d in profile.primary_domains + profile.secondary_domains}
    if not role_terms or not candidate_domains:
        return 0.5
    hits = sum(1 for d in candidate_domains if any(rt in d or d in rt for rt in role_terms))
    return round(min(1.0, hits / max(len(candidate_domains), 1)), 3)


def _seniority_alignment(profile: CandidateProfile, role_def) -> float:
    """Higher when candidate seniority index aligns with role leadership intensity."""
    candidate_idx = _SENIORITY_INDEX.get(profile.current_seniority, 3)
    expected = role_def.leadership_intensity * 8.0
    gap = abs(candidate_idx - expected) / 8.0
    return round(max(0.0, 1.0 - gap), 3)


def calculate_role_family_distance(
    candidate_profile: CandidateProfile,
    role_family: RoleFamilyId | str,
) -> dict:
    """
    Weighted proximity between a candidate profile and a role family.

    Returns score (0–1), distance (1 - score), and structured explanations.
    """
    family_id = _resolve_role_family(role_family)
    role_def = get_role_family(family_id)

    capability_scores = infer_capabilities(normalize_skills(candidate_profile.top_skills))

    cap_overlap, cap_evidence = _capability_overlap(
        capability_scores,
        role_def.primary_capabilities,
        role_def.secondary_capabilities,
    )

    candidate_leadership = _candidate_leadership_score(candidate_profile)
    leadership_align = round(
        1.0 - abs(candidate_leadership - role_def.leadership_intensity), 3
    )

    transformation_align = round(
        1.0 - abs(candidate_profile.transformation_focus - role_def.transformation_intensity),
        3,
    )

    candidate_enterprise = _ENTERPRISE_INDEX.get(
        candidate_profile.enterprise_experience, 0.0
    )
    enterprise_align = round(
        1.0 - abs(candidate_enterprise - role_def.enterprise_depth), 3
    )

    domain_align = _domain_overlap(candidate_profile, family_id)
    seniority_align = _seniority_alignment(candidate_profile, role_def)

    components = {
        "capability": cap_overlap,
        "leadership": leadership_align,
        "transformation": transformation_align,
        "enterprise": enterprise_align,
        "domain": domain_align,
        "seniority": seniority_align,
    }

    score = round(
        sum(components[k] * _WEIGHTS[k] for k in _WEIGHTS),
        3,
    )

    # Apply semantic distance penalty from primary track
    if candidate_profile.primary_career_track != family_id:
        semantic_dist = compute_family_distance(
            candidate_profile.primary_career_track, family_id
        )
        score = round(score * (1.0 - semantic_dist * 0.35), 3)

    score = min(1.0, max(0.0, score))
    distance = round(1.0 - score, 3)

    explanations: list[str] = []
    if cap_evidence:
        explanations.append(
            f"Capability overlap {cap_overlap:.2f} via {', '.join(cap_evidence[:4])}"
        )
    else:
        explanations.append(f"Capability overlap {cap_overlap:.2f} (limited direct evidence)")

    explanations.append(
        f"Leadership alignment {leadership_align:.2f} "
        f"(candidate {candidate_leadership:.2f} vs role {role_def.leadership_intensity:.2f})"
    )
    explanations.append(
        f"Transformation alignment {transformation_align:.2f} "
        f"(focus {candidate_profile.transformation_focus:.2f})"
    )
    explanations.append(
        f"Enterprise depth alignment {enterprise_align:.2f} "
        f"({candidate_profile.enterprise_experience.value})"
    )
    explanations.append(f"Domain overlap {domain_align:.2f}")
    explanations.append(f"Seniority alignment {seniority_align:.2f}")

    return {
        "score": score,
        "distance": distance,
        "components": components,
        "explanations": explanations,
    }


def rank_role_families_by_fit(
    candidate_profile: CandidateProfile,
) -> list[tuple[RoleFamilyId, dict]]:
    """Rank all role families by capability-aware fit (higher score = closer)."""
    ranked: list[tuple[RoleFamilyId, dict]] = []
    for family_id in ROLE_FAMILIES:
        result = calculate_role_family_distance(candidate_profile, family_id)
        ranked.append((family_id, result))
    return sorted(ranked, key=lambda x: -x[1]["score"])
