"""Deterministic regression tests for candidate ↔ job matching."""

from __future__ import annotations

import math

import pytest

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.job_parser import parse_job_description
from career_intelligence_engine.matching.job_match_engine import match_candidate_to_job
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.capability_vectors import CAPABILITY_DIMENSIONS
from career_intelligence_engine.tests.fixtures.calibration_resumes import (
    RESUME_OPERATIONS_MANAGER,
    RESUME_PRODUCT_MANAGER,
    RESUME_SIVAKUMAR_STYLE,
    RESUME_TPM,
)
from career_intelligence_engine.tests.fixtures.sample_jds import (
    JD_AI_TRANSFORMATION,
    JD_OPERATIONS,
    JD_PRODUCT,
    JD_RELEASE_GOVERNANCE,
    JD_TPM,
)


@pytest.fixture
def engine() -> CareerIdentityEngine:
    return CareerIdentityEngine()


def _analyze(engine: CareerIdentityEngine, text: str):
    return engine.analyze_text(text)


def test_tpm_resume_matches_tpm_jd_high(engine: CareerIdentityEngine) -> None:
    profile = _analyze(engine, RESUME_TPM)
    job = parse_job_description(JD_TPM)
    result = match_candidate_to_job(profile, job)
    assert result.overall_match_score >= 0.50
    assert result.capability_similarity >= 0.45
    assert result.gate_passed
    assert result.fit_summary
    assert result.strengths


def test_tpm_resume_matches_release_governance_jd(engine: CareerIdentityEngine) -> None:
    profile = _analyze(engine, RESUME_SIVAKUMAR_STYLE)
    job = parse_job_description(JD_RELEASE_GOVERNANCE)
    result = match_candidate_to_job(profile, job)
    assert result.overall_match_score >= 0.45
    assert "Release" in " ".join(result.dominant_match_dimensions) or result.capability_similarity >= 0.40


def test_product_resume_matches_product_jd(engine: CareerIdentityEngine) -> None:
    profile = _analyze(engine, RESUME_PRODUCT_MANAGER)
    job = parse_job_description(JD_PRODUCT)
    result = match_candidate_to_job(profile, job)
    assert result.gate_passed
    assert result.overall_match_score >= 0.45


def test_product_jd_gates_tpm_resume(engine: CareerIdentityEngine) -> None:
    profile = _analyze(engine, RESUME_TPM)
    job = parse_job_description(JD_PRODUCT)
    result = match_candidate_to_job(profile, job)
    assert not result.gate_passed or result.overall_match_score <= 0.55


def test_operations_resume_matches_operations_jd(engine: CareerIdentityEngine) -> None:
    profile = _analyze(engine, RESUME_OPERATIONS_MANAGER)
    job = parse_job_description(JD_OPERATIONS)
    result = match_candidate_to_job(profile, job)
    assert result.gate_passed
    assert result.overall_match_score >= 0.40


def test_ai_transformation_jd_explainability(engine: CareerIdentityEngine) -> None:
    profile = _analyze(engine, RESUME_SIVAKUMAR_STYLE)
    job = parse_job_description(JD_AI_TRANSFORMATION)
    result = match_candidate_to_job(profile, job)
    assert result.fit_summary
    assert isinstance(result.gaps, list)
    assert isinstance(result.recommended_resume_improvements, list)
    assert result.scorer_path == "deterministic_job_match_v1"


def test_match_deterministic(engine: CareerIdentityEngine) -> None:
    profile = _analyze(engine, RESUME_TPM)
    job = parse_job_description(JD_TPM)
    a = match_candidate_to_job(profile, job)
    b = match_candidate_to_job(profile, job)
    assert a.overall_match_score == b.overall_match_score
    assert a.capability_similarity == b.capability_similarity
    assert a.fit_summary == b.fit_summary


def test_no_embedding_apis_used() -> None:
    """Ensure match engine imports only deterministic modules."""
    import career_intelligence_engine.matching.job_match_engine as mod

    source = open(mod.__file__, encoding="utf-8").read().lower()
    assert "openai" not in source
    assert "embedding" not in source


def test_match_result_vector_dimensions(engine: CareerIdentityEngine) -> None:
    profile = _analyze(engine, RESUME_TPM)
    job = parse_job_description(JD_TPM)
    assert set(job.capability_vector.keys()) == set(CAPABILITY_DIMENSIONS)
    norm = math.sqrt(sum(v * v for v in job.capability_vector.values()))
    assert norm == pytest.approx(1.0, abs=0.02) or norm == pytest.approx(0.0, abs=0.01)
