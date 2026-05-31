"""Tests for job matching interfaces."""

from __future__ import annotations

from career_intelligence_engine.intelligence.future_interfaces import (
    CandidateJobMatcherImpl,
    JobDescriptionParserImpl,
    ParsedJobDescription,
)
from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.tests.fixtures.sample_jds import JD_TPM


def test_parsed_jd_dataclass() -> None:
    jd = ParsedJobDescription(raw_text="Senior TPM role", title="TPM")
    assert jd.raw_text == "Senior TPM role"
    assert jd.title == "TPM"


def test_job_parser_impl() -> None:
    parser = JobDescriptionParserImpl()
    job = parser.parse(JD_TPM)
    assert job.capability_vector
    assert job.primary_role_family


def test_candidate_job_matcher_impl() -> None:
    profile = CareerIdentityEngine().analyze_text(
        "Senior TPM | Co | 2020 – Present\n• Release train SDLC governance"
    )
    job = JobDescriptionParserImpl().parse(JD_TPM)
    result = CandidateJobMatcherImpl().match(profile, job)
    assert result.overall_match_score >= 0.0
    assert result.fit_summary
