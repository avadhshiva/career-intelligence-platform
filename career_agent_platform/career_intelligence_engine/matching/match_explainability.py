"""Recruiter-readable match explanations."""

from __future__ import annotations

from career_intelligence_engine.narrative_phrasing import (
    compose_positioning_summary,
    interpret_profile_pattern,
    phrase_gap,
    phrase_missing_capability,
    phrase_strength,
    resume_improvements_for_job,
)
from career_intelligence_engine.matching.result import JobMatchResult
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.ontology.capability_vectors import (
    dimension_contributions,
)
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES


def _job_narrative_context(job: JobProfile) -> str:
    return f"{job.title or ''}:{job.primary_role_family.value}"


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

    dominant_ids: list[str] = []
    weak_ids: list[str] = []
    ctx = _job_narrative_context(job)

    for dim, contrib in dominant[:4]:
        if contrib >= 0.08:
            job_weight = job_vec.get(dim, 0.0)
            if job_weight >= 0.15:
                strengths.append(phrase_strength(dim, contrib, context=ctx))
                dominant_ids.append(dim)

    for dim, contrib in weak[:4]:
        cand_val = cand_vec.get(dim, 0.0)
        job_weight = job_vec.get(dim, 0.0)
        if job_weight >= 0.20 and cand_val < 0.25:
            gaps.append(phrase_gap(dim, cand_val, job_weight, context=ctx))
            weak_ids.append(dim)

    if result.missing_capabilities:
        for item in result.missing_capabilities[:5]:
            humanized = phrase_missing_capability(item)
            if humanized not in gaps:
                gaps.append(humanized)

    if not result.gate_passed:
        risks.extend(result.gate_reasons)

    improvements.extend(
        resume_improvements_for_job(
            job,
            gate_failed=not result.gate_passed,
            product_low=_candidate_product(profile) < 0.20,
            ops_low=_candidate_ops(profile) < 0.15,
            arch_low=_candidate_arch(profile) <= 0.0,
        ),
    )

    job_display = ROLE_FAMILIES[job.primary_role_family].display_name
    strategic_pattern = interpret_profile_pattern(dominant_ids, weak_ids, job)
    gate_reason = result.gate_reasons[0] if result.gate_reasons else ""

    fit_summary = compose_positioning_summary(
        job_display=job_display,
        score=result.overall_match_score,
        gate_passed=result.gate_passed,
        gate_reason=gate_reason,
        dominant_dims=dominant_ids,
        weak_dims=weak_ids,
        strategic_pattern=strategic_pattern,
    )

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
