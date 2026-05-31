"""Recruiter-readable match explanations."""

from __future__ import annotations

from career_intelligence_engine.matching.result import JobMatchResult
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.ontology.capability_vectors import (
    DIMENSION_LABELS,
    dimension_contributions,
)
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES


def _label_dims(dims: list[str]) -> list[str]:
    return [DIMENSION_LABELS.get(d, d.replace("_", " ").title()) for d in dims]


def build_match_explanation(
    profile: CandidateProfile,
    job: JobProfile,
    result: JobMatchResult,
) -> dict[str, list[str] | str]:
    """Produce strengths, gaps, risks, and resume improvement recommendations."""
    cand_vec = profile.capability_vector or {}
    job_vec = job.capability_vector or {}
    dominant, weak = dimension_contributions(cand_vec, job_vec, top_n=5)

    strengths: list[str] = []
    gaps: list[str] = []
    risks: list[str] = list(result.risks)
    improvements: list[str] = []

    job_display = ROLE_FAMILIES[job.primary_role_family].display_name

    for dim, contrib in dominant[:4]:
        if contrib >= 0.08:
            label = DIMENSION_LABELS.get(dim, dim)
            job_weight = job_vec.get(dim, 0.0)
            if job_weight >= 0.15:
                strengths.append(
                    f"Strong alignment on {label} (job weight {job_weight:.0%})"
                )

    for dim, contrib in weak[:4]:
        label = DIMENSION_LABELS.get(dim, dim)
        cand_val = cand_vec.get(dim, 0.0)
        job_weight = job_vec.get(dim, 0.0)
        if job_weight >= 0.20 and cand_val < 0.25:
            gaps.append(f"{label}: job requires {job_weight:.0%}, candidate shows {cand_val:.0%}")

    if result.missing_capabilities:
        for item in result.missing_capabilities[:5]:
            if item not in gaps:
                gaps.append(item)

    if not result.gate_passed:
        risks.extend(result.gate_reasons)
        improvements.append(
            "Address hard gate failures before applying — missing role-critical ownership evidence."
        )

    if job.is_product_heavy and _candidate_product(profile) < 0.20:
        improvements.append(
            "Add product roadmap ownership, customer discovery, and go-to-market outcomes."
        )
    if job.is_operations_heavy and _candidate_ops(profile) < 0.15:
        improvements.append(
            "Add run-state operations, SLA/incident management, and production support evidence."
        )
    if job.is_architecture_heavy and _candidate_arch(profile) <= 0.0:
        improvements.append(
            "Add architecture review board, solution architecture, or enterprise architecture coordination."
        )
    if job.is_ai_transformation:
        improvements.append(
            "Add enterprise AI strategy ownership, operating model redesign, and transformation metrics."
        )
    if job.is_release_governance_heavy:
        improvements.append(
            "Highlight release train, PI planning, SDLC governance, and deployment governance ownership."
        )

    fit_summary = _compose_fit_summary(profile, job, result, strengths, gaps)

    return {
        "fit_summary": fit_summary,
        "strengths": strengths[:6],
        "gaps": gaps[:6],
        "risks": risks[:6],
        "recommended_resume_improvements": improvements[:5],
    }


def _candidate_product(profile: CandidateProfile) -> float:
    raw = profile.capability_raw_scores or {}
    return max(raw.get("product_ownership_depth", 0.0), raw.get("product_thinking", 0.0))


def _candidate_ops(profile: CandidateProfile) -> float:
    raw = profile.capability_raw_scores or {}
    return raw.get("operational_management", 0.0)


def _candidate_arch(profile: CandidateProfile) -> float:
    raw = profile.capability_raw_scores or {}
    return raw.get("architecture_coordination", 0.0)


def _compose_fit_summary(
    profile: CandidateProfile,
    job: JobProfile,
    result: JobMatchResult,
    strengths: list[str],
    gaps: list[str],
) -> str:
    job_name = ROLE_FAMILIES[job.primary_role_family].display_name
    score_pct = int(result.overall_match_score * 100)

    if not result.gate_passed:
        return (
            f"Candidate does not meet hard eligibility requirements for this {job_name} role "
            f"(match capped at {score_pct}%). "
            + (result.gate_reasons[0] if result.gate_reasons else "Missing gate evidence.")
        )

    if result.overall_match_score >= 0.75:
        lead = (
            f"Candidate strongly matches {job_name} requirements "
            f"with {score_pct}% overall fit."
        )
    elif result.overall_match_score >= 0.55:
        lead = (
            f"Candidate shows moderate fit ({score_pct}%) for this {job_name} role "
            "with identifiable strengths and gaps."
        )
    else:
        lead = (
            f"Candidate shows limited fit ({score_pct}%) for this {job_name} role; "
            "significant capability gaps remain."
        )

    strength_clause = ""
    if strengths:
        top_labels = []
        for s in strengths[:2]:
            if "alignment on" in s:
                top_labels.append(s.split("alignment on ", 1)[-1].split(" (")[0])
        if top_labels:
            strength_clause = (
                f" Strongest dimensions: {', '.join(top_labels)}."
            )

    gap_clause = ""
    if gaps:
        gap_clause = f" Key gaps: {gaps[0].split(':')[0] if ':' in gaps[0] else gaps[0]}."

    return lead + strength_clause + gap_clause
