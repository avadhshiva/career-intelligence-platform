"""Structured, evidence-backed explainability for career identity outputs."""

from __future__ import annotations

from career_intelligence_engine.intelligence.capability_density import score_capability_density
from career_intelligence_engine.intelligence.capability_inference import infer_capabilities
from career_intelligence_engine.intelligence.executive_signals import detect_executive_signals
from career_intelligence_engine.intelligence.semantic_distance import compute_family_distance
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.capability_graph import (
    CAPABILITY_CLUSTERS,
    normalize_skills,
)
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES

_CAP_DISPLAY = {cid: cid.replace("_", " ").title() for cid in CAPABILITY_CLUSTERS}

_SIGNAL_TRANSLATIONS: dict[str, dict[str, str]] = {
    "transformation": {
        "transformation_mentions": "Resume demonstrates organizational or digital transformation experience.",
        "ai_strategy_mentions": "Resume contains repeated enterprise AI strategy ownership signals.",
        "ai_transformation_lead": "Candidate shows AI transformation leadership maturity.",
        "ai_scaling": "Evidence of scaling AI initiatives from pilot to production.",
        "ai_pilot": "AI pilot and proof-of-concept experience detected.",
        "ai_awareness": "Foundational AI awareness signals present.",
    },
    "leadership": {
        "ic_hands_on": "Individual contributor hands-on execution pattern detected.",
        "team_lead_scope": "Team lead scope with cross-functional coordination.",
        "people_management": "Direct people management and team leadership evidence.",
        "org_scope": "Organizational scope spanning departments or matrix structures.",
        "executive_scope": "Executive-level stakeholder and board interaction signals.",
    },
    "seniority": {},
    "domain": {},
}


def humanize_signals(signals: list[str], category: str) -> list[str]:
    """Convert internal signal keys to human-readable explanations."""
    translations = _SIGNAL_TRANSLATIONS.get(category, {})
    result: list[str] = []
    for sig in signals:
        if sig in translations:
            result.append(translations[sig])
            continue
        if ":" in sig:
            key, count = sig.split(":", 1)
            if key in translations:
                base = translations[key]
                if count.isdigit() and int(count) > 1:
                    result.append(f"{base} ({count} occurrences).")
                else:
                    result.append(base)
                continue
        if sig.startswith("seniority_prior:"):
            level = sig.split(":", 1)[1]
            result.append(f"Seniority inferred at {level.replace('_', ' ')} level from title patterns.")
            continue
        if sig == "deep_enterprise_language":
            result.append(
                "Candidate demonstrates large-enterprise governance and cross-functional delivery language."
            )
            continue
        result.append(sig.replace("_", " ").capitalize() + ".")
    return result


def _top_capabilities(profile: CandidateProfile, limit: int = 5) -> list[tuple[str, float]]:
    caps = infer_capabilities(normalize_skills(profile.top_skills))
    ranked = sorted(
        ((cid, data["score"]) for cid, data in caps.items()),
        key=lambda x: -x[1],
    )
    return ranked[:limit]


def _reasons_for_family(
    profile: CandidateProfile,
    family_id: RoleFamilyId,
    capability_scores: dict[str, dict],
) -> list[str]:
    """Build non-generic reasons only when evidence exists."""
    role_def = ROLE_FAMILIES[family_id]
    reasons: list[str] = []

    for cap_id in role_def.primary_capabilities:
        entry = capability_scores.get(cap_id)
        if entry and entry.get("score", 0) >= 0.2:
            label = _CAP_DISPLAY.get(cap_id, cap_id)
            ev = entry.get("evidence", [])
            if ev:
                reasons.append(f"Strong {label} signals ({', '.join(ev[:3])})")
            else:
                reasons.append(f"Strong {label} signals")

    if profile.governance_experience >= 0.4 and role_def.leadership_intensity >= 0.6:
        reasons.append("Cross-functional governance emphasis aligns with role family leadership profile.")

    if profile.stakeholder_complexity >= 0.4 and role_def.leadership_intensity >= 0.5:
        reasons.append("Executive stakeholder coordination indicators match role requirements.")

    if (
        profile.transformation_focus >= 0.3
        and role_def.transformation_intensity >= 0.5
    ):
        reasons.append("Transformation ownership aligns with role family transformation intensity.")

    if profile.enterprise_experience.value in ("strong", "deep") and role_def.enterprise_depth >= 0.6:
        reasons.append(
            f"Enterprise exposure ({profile.enterprise_experience.value}) matches the depth required for this track."
        )

    if profile.delivery_orientation >= 0.4 and "delivery" in role_def.display_name.lower():
        reasons.append("Delivery-oriented experience pattern supports this role family.")

    primary_score = profile.role_family_scores.get(family_id.value, 0)
    if primary_score > 0:
        dist = compute_family_distance(profile.primary_career_track, family_id)
        reasons.append(
            f"Calibrated role-family score {primary_score:.2f} with semantic distance {dist:.2f}."
        )

    return reasons[:6]


def generate_structured_explanations(profile: CandidateProfile) -> dict[str, list[str] | dict]:
    """
    Produce structured reasons for career identity dimensions.

    All strings are derived from profile fields and capability evidence — no LLM output.
    """
    capability_scores = infer_capabilities(normalize_skills(profile.top_skills))
    top_caps = _top_capabilities(profile)

    result: dict[str, list[str] | dict] = {}

    primary = profile.primary_career_track
    result[f"why_{primary.value}"] = _reasons_for_family(profile, primary, capability_scores)

    for adj in profile.adjacent_role_families:
        key = f"why_{adj.value}"
        if key not in result:
            result[key] = _reasons_for_family(profile, adj, capability_scores)

    transformation_reasons: list[str] = []
    if profile.transformation_focus > 0.2:
        transformation_reasons.append(
            f"Transformation focus score indicates sustained change-leadership exposure ({profile.transformation_focus:.2f})."
        )
    for cap_id, _ in top_caps:
        if cap_id in ("ai_transformation", "change_transformation", "ai_governance_risk"):
            ev = capability_scores.get(cap_id, {}).get("evidence", [])
            label = _CAP_DISPLAY.get(cap_id, cap_id)
            if ev:
                transformation_reasons.append(
                    f"Resume shows {label.lower()} evidence through {', '.join(ev[:3])}."
                )
    if profile.ai_maturity.value not in ("none", "awareness"):
        transformation_reasons.append(
            f"AI maturity inferred at {profile.ai_maturity.value.replace('_', ' ')} level."
        )
    result["transformation_focus"] = transformation_reasons

    leadership_reasons: list[str] = []
    if profile.governance_experience >= 0.3:
        leadership_reasons.append(
            f"Governance experience score reflects enterprise program oversight ({profile.governance_experience:.2f})."
        )
    if profile.stakeholder_complexity >= 0.3:
        leadership_reasons.append(
            f"Stakeholder complexity indicates executive-level coordination ({profile.stakeholder_complexity:.2f})."
        )
    if profile.leadership_level.value != "unknown":
        leadership_reasons.append(
            f"Leadership level inferred as {profile.leadership_level.value.replace('_', ' ')}."
        )
    result["leadership_inference"] = leadership_reasons

    enterprise_reasons: list[str] = []
    if profile.enterprise_experience.value != "none":
        enterprise_reasons.append(
            f"Enterprise exposure assessed as {profile.enterprise_experience.value}."
        )
    if profile.years_experience and profile.years_experience >= 8:
        enterprise_reasons.append(
            f"{profile.years_experience:.0f}+ years of professional tenure supports enterprise depth."
        )
    for cap_id, score in top_caps:
        if cap_id == "enterprise_platforms" and score >= 0.2:
            ev = capability_scores.get(cap_id, {}).get("evidence", [])
            enterprise_reasons.append(
                f"Enterprise platform signals: {', '.join(ev[:4])}." if ev
                else "Enterprise platform capability match detected."
            )
    result["enterprise_exposure"] = enterprise_reasons

    if top_caps:
        result["top_capabilities"] = [
            f"{_CAP_DISPLAY.get(cid, cid)} ({score:.2f})" for cid, score in top_caps
        ]

    return result
