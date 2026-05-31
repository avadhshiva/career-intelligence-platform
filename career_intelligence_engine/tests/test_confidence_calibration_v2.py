"""Tests for Confidence Calibration V2 and margin separation."""

from __future__ import annotations

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.confidence import compute_confidence
from career_intelligence_engine.intelligence.confidence_calibration_v2 import (
    build_confidence_calibration_v2,
)
from career_intelligence_engine.intelligence.role_family_scoring import (
    SCORER_PATH,
    compute_unified_from_parsed,
    load_canonical_unified_from_profile,
)
from career_intelligence_engine.models.ontology import RoleFamilyId, ParsedResume
from career_intelligence_engine.ontology.role_family_calibration import (
    build_calibration_context,
)
from career_intelligence_engine.tests.benchmark_resumes import BENCHMARK_FIXTURE_BY_ID
from career_intelligence_engine.tests.fixtures.calibration_resumes import (
    RESUME_OPERATIONS_MANAGER,
    RESUME_PRODUCT_MANAGER,
    RESUME_TPM,
)


def _trace(profile) -> dict[str, float]:
    return {
        r["role_family"]: r["final_score"]
        for r in profile.explanations["score_trace"]
    }


def test_tpm_resume_tpm_outranks_release_governance() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_TPM)
    scores = _trace(profile)
    assert profile.primary_career_track == RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT
    assert scores["technical_program_management"] > scores["release_governance"]
    assert (
        scores["technical_program_management"] - scores["release_governance"]
    ) >= 0.05
    assert profile.explanations.get("scorer_path") == SCORER_PATH


def test_release_governance_wins_with_explicit_release_ownership() -> None:
    fixture = BENCHMARK_FIXTURE_BY_ID["release_governance_lead"]
    profile = CareerIdentityEngine().analyze_text(fixture.resume_text)
    scores = _trace(profile)
    assert profile.primary_career_track == RoleFamilyId.RELEASE_GOVERNANCE
    assert scores["release_governance"] > scores["technical_program_management"]
    margin = profile.explanations.get("margin_calibration_v2", {})
    assert margin.get("dominance_margin", 0) >= 0.08


def test_product_and_operations_excluded_without_gates() -> None:
    engine = CareerIdentityEngine()
    for text in (RESUME_TPM, RESUME_PRODUCT_MANAGER, RESUME_OPERATIONS_MANAGER):
        profile = engine.analyze_text(text)
        matrix = profile.explanations.get("eligibility_matrix", {})
        if text == RESUME_TPM:
            assert matrix["product_management"]["eligible_for_ranking"] is False
            assert matrix["operations"]["eligible_for_ranking"] is False
        if text == RESUME_PRODUCT_MANAGER:
            assert matrix["product_management"]["eligible_for_ranking"] is True
            assert profile.primary_career_track in (
                RoleFamilyId.PRODUCT_MANAGEMENT,
                RoleFamilyId.PRODUCT_DELIVERY,
            )
        if text == RESUME_OPERATIONS_MANAGER:
            assert matrix["operations"]["eligible_for_ranking"] is True


def test_confidence_increases_with_score_separation() -> None:
    engine = CareerIdentityEngine()
    ambiguous = engine.analyze_text(
        "Program Manager | Co | 2020 – Present\n"
        "• Stakeholder management and cross-functional delivery\n"
    )
    separated = engine.analyze_text(RESUME_TPM)
    assert separated.confidence_result is not None
    assert ambiguous.confidence_result is not None
    assert (
        separated.confidence_result.dominance_margin
        >= ambiguous.confidence_result.dominance_margin
    )
    assert (
        separated.confidence_result.score_margin_confidence
        >= ambiguous.confidence_result.score_margin_confidence
    )
    assert separated.confidence_result.confidence_score > (
        ambiguous.confidence_result.confidence_score
    )


def test_confidence_v2_outputs_exposed() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_TPM)
    conf = profile.confidence_result
    assert conf is not None
    data = conf.to_dict()
    for key in (
        "dominance_margin",
        "ambiguity_level",
        "ranking_stability",
        "score_margin_confidence",
        "evidence_density_confidence",
        "contamination_risk",
        "ambiguity_penalty",
        "calibration_strength",
        "confidence_contributors",
        "confidence_penalties",
    ):
        assert key in data
    assert "margin_calibration_v2" in profile.explanations


def test_canonical_pipeline_path_unchanged() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_TPM)
    assert profile.explanations["canonical_ranking"]["scorer_path"] == SCORER_PATH
    unified = load_canonical_unified_from_profile(profile)
    assert unified is not None
    assert unified.margin_calibration is not None


def test_margin_calibration_deterministic() -> None:
    parsed = ParsedResume(raw_text=RESUME_TPM, bullets=[], job_titles=[])
    cal = build_calibration_context(parsed)
    ontology = {fid: 10.0 for fid in RoleFamilyId}
    u1 = compute_unified_from_parsed(parsed, ontology, cal_ctx=cal)
    u2 = compute_unified_from_parsed(parsed, ontology, cal_ctx=cal)
    assert u1.primary == u2.primary
    assert u1.margin_calibration == u2.margin_calibration


def test_program_leadership_not_zeroed_with_portfolio_gate() -> None:
    """Moderate PMO gate evidence should not be over-suppressed under TPM title."""
    from career_intelligence_engine.tests.fixtures.calibration_resumes import (
        RESUME_SIVAKUMAR_STYLE,
    )

    profile = CareerIdentityEngine().analyze_text(RESUME_SIVAKUMAR_STYLE)
    scores = _trace(profile)
    assert scores["program_leadership"] > 0.0
    assert scores["technical_program_management"] > scores["program_leadership"]


def test_build_confidence_calibration_v2_from_unified() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_TPM)
    unified = load_canonical_unified_from_profile(profile)
    assert unified is not None
    cal = build_confidence_calibration_v2(
        profile, unified, evidence_density=0.5, top_gap=0.1
    )
    assert 0.0 <= cal.score_margin_confidence <= 1.0
    assert cal.ambiguity_level in ("LOW", "MEDIUM", "HIGH")
    result = compute_confidence(profile, unified=unified)
    assert result.dominance_margin == cal.dominance_margin or result.top_gap >= 0
