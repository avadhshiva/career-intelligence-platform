"""Deterministic candidate ↔ job match engine."""

from __future__ import annotations

from typing import Any

from career_intelligence_engine.intelligence.gap_analysis import (
    _MISSING_THRESHOLD,
    _STRONG_TARGET,
    _WEAK_THRESHOLD,
)
from career_intelligence_engine.intelligence.job_parser import parse_job_description
from career_intelligence_engine.matching.job_gating import evaluate_job_gates
from career_intelligence_engine.matching.match_explainability import build_match_explanation
from career_intelligence_engine.matching.result import JobMatchResult
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.models.ontology import SeniorityLevel
from career_intelligence_engine.ontology.capability_vectors import (
    CAPABILITY_DIMENSIONS,
    DIMENSION_LABELS,
    cosine_similarity,
    dimension_contributions,
    label_dimension,
)
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES

_SENIORITY_ORDER = [
    SeniorityLevel.INTERN,
    SeniorityLevel.JUNIOR,
    SeniorityLevel.MID,
    SeniorityLevel.SENIOR,
    SeniorityLevel.LEAD,
    SeniorityLevel.PRINCIPAL,
    SeniorityLevel.DIRECTOR,
    SeniorityLevel.VP,
    SeniorityLevel.C_LEVEL,
    SeniorityLevel.UNKNOWN,
]

_WEIGHTS = {
    "capability_similarity": 0.45,
    "eligibility_fit": 0.20,
    "seniority_fit": 0.10,
    "transformation_fit": 0.10,
    "architecture_fit": 0.08,
    "governance_fit": 0.07,
}


def _seniority_index(level: SeniorityLevel) -> int:
    try:
        return _SENIORITY_ORDER.index(level)
    except ValueError:
        return len(_SENIORITY_ORDER) - 1


def _compute_seniority_fit(profile: CandidateProfile, job: JobProfile) -> float:
    cand_idx = _seniority_index(profile.current_seniority)
    job_idx = _seniority_index(job.required_seniority)
    if job.required_seniority == SeniorityLevel.UNKNOWN:
        return 0.85
    diff = abs(cand_idx - job_idx)
    if diff == 0:
        return 1.0
    if diff == 1:
        return 0.85
    if diff == 2:
        return 0.65
    if cand_idx > job_idx:
        return max(0.55, 0.90 - diff * 0.08)
    return max(0.35, 0.75 - diff * 0.15)


def _compute_transformation_fit(profile: CandidateProfile, job: JobProfile) -> float:
    job_trans = 0.0
    if job.transformation_type in ("ai", "digital", "operating_model", "cloud"):
        job_trans = 0.75
    if job.is_ai_transformation:
        job_trans = max(job_trans, 0.9)
    if job_trans <= 0:
        return 0.9

    cand_trans = profile.transformation_focus
    cand_ai = {
        "none": 0.0,
        "awareness": 0.2,
        "pilot": 0.35,
        "practitioner": 0.55,
        "transformation_lead": 0.75,
        "enterprise_ai_owner": 0.95,
    }.get(profile.ai_maturity.value, 0.0)

    combined = min(1.0, (cand_trans * 0.5 + cand_ai * 0.5))
    return round(min(1.0, combined / job_trans * 0.95 + 0.05), 4)


def _compute_architecture_fit(profile: CandidateProfile, job: JobProfile) -> float:
    if not job.is_architecture_heavy and job.architecture_depth < 0.20:
        return 0.9
    cand = (profile.capability_raw_scores or {}).get("architecture_coordination", 0.0)
    required = max(job.architecture_depth, 0.25)
    return round(min(1.0, cand / required), 4)


def _compute_governance_fit(profile: CandidateProfile, job: JobProfile) -> float:
    if job.governance_intensity < 0.25:
        return 0.9
    cand = profile.governance_experience
    required = job.governance_intensity
    return round(min(1.0, cand / max(required, 0.15)), 4)


def _missing_capabilities(
    profile: CandidateProfile,
    job: JobProfile,
) -> list[str]:
    missing: list[str] = []
    cand_vec = profile.capability_vector or {}
    job_vec = job.capability_vector or {}
    gaps: list[tuple[str, float]] = []
    for dim in CAPABILITY_DIMENSIONS:
        jw = float(job_vec.get(dim, 0.0))
        if jw < _MISSING_THRESHOLD:
            continue
        cv = float(cand_vec.get(dim, 0.0))
        gap = jw - cv
        if gap > _MISSING_THRESHOLD:
            gaps.append((dim, gap))
    gaps.sort(key=lambda x: -x[1])
    for dim, _ in gaps[:8]:
        cv = float(cand_vec.get(dim, 0.0))
        jw = float(job_vec.get(dim, 0.0))
        label = DIMENSION_LABELS.get(dim, dim)
        if cv < _MISSING_THRESHOLD:
            missing.append(label)
        elif cv < _WEAK_THRESHOLD and jw >= _STRONG_TARGET:
            missing.append(f"{label} (weak)")
    return missing


def _risk_penalties(
    profile: CandidateProfile,
    job: JobProfile,
    gate_reasons: list[str],
) -> tuple[list[str], float]:
    penalties: list[str] = []
    total = 0.0

    if gate_reasons:
        penalties.extend(gate_reasons[:3])
        total += 0.18

    excluded = profile.explanations.get("excluded_from_ranking") or []
    job_family = job.primary_role_family.value
    if job_family in excluded:
        penalties.append(f"Candidate excluded from {job_family} role-family ranking")
        total += 0.12

    contamination = profile.explanations.get("contamination_signals") or []
    if contamination:
        penalties.append("Career identity contamination signals detected")
        total += 0.05

    conf = profile.confidence_result
    if conf and conf.confidence_score < 0.45:
        penalties.append("Low profile confidence — match uncertainty elevated")
        total += 0.06

    return penalties, min(0.25, total)


def match_candidate_to_job(
    profile: CandidateProfile,
    job: JobProfile,
) -> JobMatchResult:
    """Compute full deterministic match between candidate and job."""
    cand_vec = profile.capability_vector or {}
    job_vec = job.capability_vector or {}

    capability_sim = cosine_similarity(cand_vec, job_vec)
    gate = evaluate_job_gates(profile, job)
    seniority_fit = _compute_seniority_fit(profile, job)
    transformation_fit = _compute_transformation_fit(profile, job)
    architecture_fit = _compute_architecture_fit(profile, job)
    governance_fit = _compute_governance_fit(profile, job)

    eligibility_fit = gate.eligibility_fit
    risk_list, risk_deduction = _risk_penalties(profile, job, gate.reasons)

    raw_score = (
        _WEIGHTS["capability_similarity"] * capability_sim
        + _WEIGHTS["eligibility_fit"] * eligibility_fit
        + _WEIGHTS["seniority_fit"] * seniority_fit
        + _WEIGHTS["transformation_fit"] * transformation_fit
        + _WEIGHTS["architecture_fit"] * architecture_fit
        + _WEIGHTS["governance_fit"] * governance_fit
        - risk_deduction
    )
    overall = round(max(0.0, min(1.0, raw_score)), 4)

    if not gate.passed and gate.capped_score is not None:
        overall = min(overall, gate.capped_score)

    dominant_raw, _ = dimension_contributions(cand_vec, job_vec, top_n=5)
    dominant_labels = [label_dimension(d) for d, _ in dominant_raw if _ >= 0.05]

    missing = _missing_capabilities(profile, job)

    confidence = round(
        min(
            0.95,
            0.5
            + capability_sim * 0.25
            + (profile.confidence_result.confidence_score if profile.confidence_result else 0.5) * 0.2
            + (0.15 if gate.passed else 0.0),
        ),
        4,
    )

    partial = JobMatchResult(
        overall_match_score=overall,
        confidence=confidence,
        capability_similarity=capability_sim,
        eligibility_fit=eligibility_fit,
        seniority_fit=seniority_fit,
        transformation_fit=transformation_fit,
        architecture_fit=architecture_fit,
        governance_fit=governance_fit,
        risk_penalties=risk_list,
        risks=risk_list,
        missing_capabilities=missing,
        dominant_match_dimensions=dominant_labels,
        gate_passed=gate.passed,
        gate_reasons=gate.reasons,
    )

    explanation = build_match_explanation(profile, job, partial)
    partial.fit_summary = explanation["fit_summary"]
    partial.strengths = explanation["strengths"]
    partial.gaps = explanation["gaps"]
    partial.risks = explanation["risks"]
    partial.recommended_resume_improvements = explanation["recommended_resume_improvements"]

    return partial


class JobMatchEngine:
    """Orchestrates JD parse + candidate match."""

    def parse_job(self, text: str) -> JobProfile:
        return parse_job_description(text)

    def match(
        self,
        profile: CandidateProfile,
        job_text: str | JobProfile,
    ) -> JobMatchResult:
        if isinstance(job_text, str):
            job = self.parse_job(job_text)
        else:
            job = job_text
        return match_candidate_to_job(profile, job)
