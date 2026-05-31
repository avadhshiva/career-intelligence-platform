"""Regression tests for Role Family Separation Calibration V2."""

from __future__ import annotations

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer
from career_intelligence_engine.tests.benchmark_resumes import BENCHMARK_FIXTURE_BY_ID
from career_intelligence_engine.tests.fixtures.calibration_resumes import (
    RESUME_TPM,
)


def _proximity_map(profile) -> dict[str, float]:
    scorer = CareerDistanceScorer()
    return {
        fid.value: result.proximity
        for fid, result in scorer.rank_role_families(profile)
    }


def test_hr_sales_finance_suppressed_on_technical_governance_resume() -> None:
    engine = CareerIdentityEngine()
    profile = engine.analyze_text(RESUME_TPM)
    prox = _proximity_map(profile)
    assert prox.get(RoleFamilyId.HR.value, 1.0) <= 0.20
    assert prox.get(RoleFamilyId.SALES.value, 1.0) <= 0.20
    assert prox.get(RoleFamilyId.FINANCE.value, 1.0) <= 0.20
    suppressed = profile.explanations.get("separation_v2", {}).get(
        "contamination_suppressed", []
    )
    assert len(suppressed) >= 1


def test_release_governance_outranks_enterprise_delivery_with_release_evidence() -> None:
    engine = CareerIdentityEngine()
    fixture = BENCHMARK_FIXTURE_BY_ID["release_governance_lead"]
    profile = engine.analyze_text(fixture.resume_text)
    prox = _proximity_map(profile)
    assert prox[RoleFamilyId.RELEASE_GOVERNANCE.value] > prox.get(
        RoleFamilyId.ENTERPRISE_DELIVERY.value, 0.0
    )


def test_tpm_architecture_boost_from_azure_devops_integration_language() -> None:
    resume = """
Senior Technical Program Manager | Cloud Co | 2019 – Present
• Azure delivery and platform migration across enterprise integration landscape
• DevOps coordination and system rollout for ERP implementation
• Technical dependency management across engineering and data teams
• Integration delivery with architecture alignment and SDLC governance
"""
    engine = CareerIdentityEngine()
    profile = engine.analyze_text(resume)
    arch = float(profile.capability_raw_scores.get("architecture_coordination", 0.0))
    assert arch >= 0.14
    prox = _proximity_map(profile)
    assert prox[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT.value] >= 0.45
    assert prox.get(RoleFamilyId.SOFTWARE_ENGINEERING.value, 0.0) < prox[
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT.value
    ]


def test_confidence_improves_with_gated_evidence_and_suppression() -> None:
    engine = CareerIdentityEngine()
    profile = engine.analyze_text(RESUME_TPM)
    conf = profile.confidence_result
    assert conf is not None
    data = conf.to_dict()
    assert "confidence_contributors" in data
    assert "gated_primary_evidence" in data["confidence_contributors"] or (
        "contamination_suppressed" in data["confidence_contributors"]
    )
    assert conf.confidence_score >= 0.35


def test_tpm_explanation_is_recruiter_readable() -> None:
    engine = CareerIdentityEngine()
    profile = engine.analyze_text(
        "Program Manager | Co | 2020 – Present\n"
        "• Stakeholder management and cross-functional delivery\n"
    )
    trace = {r["role_family"]: r for r in profile.explanations["score_trace"]}
    tpm_row = trace.get(RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT.value, {})
    explanation = tpm_row.get("explanation", "")
    assert "Low TPM proximity" not in explanation
    assert len(explanation) > 20
