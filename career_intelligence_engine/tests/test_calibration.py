"""Calibration tests — semantic separation and AI inflation control."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.evidence_calibration import (
    analyze_evidence_depth,
    infer_ai_maturity,
)
from career_intelligence_engine.models.ontology import AIMaturity, RoleFamilyId
from career_intelligence_engine.parsing.resume_parser import ResumeParser
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer
from career_intelligence_engine.tests.fixtures.calibration_resumes import (
    RESUME_AI_TRANSFORMATION_LEAD,
    RESUME_ENGINEERING_MANAGER,
    RESUME_HRBP,
    RESUME_OPERATIONS_MANAGER,
    RESUME_PRODUCT_MANAGER,
    RESUME_PROGRAM_DIRECTOR,
    RESUME_SIVAKUMAR_STYLE,
    RESUME_TPM,
)


@pytest.fixture
def engine() -> CareerIdentityEngine:
    return CareerIdentityEngine()


def _proximity_map(engine: CareerIdentityEngine, resume: str) -> dict[RoleFamilyId, float]:
    profile = engine.analyze_text(resume)
    ranked = CareerDistanceScorer().rank_role_families(profile)
    return {fid: result.proximity for fid, result in ranked}


def test_tpm_not_ai_governance_leader(engine: CareerIdentityEngine) -> None:
    scores = _proximity_map(engine, RESUME_TPM)
    assert scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT] > scores[RoleFamilyId.AI_GOVERNANCE]
    assert scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT] > scores[RoleFamilyId.AI_PROGRAM_MANAGEMENT]
    assert scores[RoleFamilyId.RELEASE_GOVERNANCE] > scores[RoleFamilyId.AI_GOVERNANCE]


def test_ai_transformation_lead_scores_high_on_ai_transform(engine: CareerIdentityEngine) -> None:
    scores = _proximity_map(engine, RESUME_AI_TRANSFORMATION_LEAD)
    assert scores[RoleFamilyId.AI_TRANSFORMATION] >= scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT]
    assert scores[RoleFamilyId.AI_GOVERNANCE] > scores[RoleFamilyId.HR]


def test_hr_near_zero_for_enterprise_tracks(engine: CareerIdentityEngine) -> None:
    scores = _proximity_map(engine, RESUME_HRBP)
    assert scores[RoleFamilyId.HR] > scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT]
    assert scores[RoleFamilyId.HR] > scores[RoleFamilyId.PROGRAM_LEADERSHIP]
    assert scores[RoleFamilyId.SALES] < 0.55
    assert scores[RoleFamilyId.FINANCE] < 0.55


def test_engineering_manager_separated_from_program_leadership(
    engine: CareerIdentityEngine,
) -> None:
    scores = _proximity_map(engine, RESUME_ENGINEERING_MANAGER)
    assert scores[RoleFamilyId.SOFTWARE_ENGINEERING] > scores[RoleFamilyId.PROGRAM_LEADERSHIP]
    assert scores[RoleFamilyId.SOFTWARE_ENGINEERING] > scores[RoleFamilyId.AI_TRANSFORMATION]


def test_operations_manager_low_on_ai_families(engine: CareerIdentityEngine) -> None:
    scores = _proximity_map(engine, RESUME_OPERATIONS_MANAGER)
    assert scores[RoleFamilyId.OPERATIONS] > scores[RoleFamilyId.AI_TRANSFORMATION]
    assert scores[RoleFamilyId.OPERATIONS] > scores[RoleFamilyId.AI_GOVERNANCE]


def test_product_manager_beats_tpm(engine: CareerIdentityEngine) -> None:
    scores = _proximity_map(engine, RESUME_PRODUCT_MANAGER)
    assert scores[RoleFamilyId.PRODUCT_MANAGEMENT] > scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT]


def test_single_ai_mention_is_awareness_not_transformation_lead() -> None:
    parsed = ResumeParser().parse_text(
        "Program Manager\n• Supported a GenAI pilot once\nSKILLS: program management"
    )
    depth = analyze_evidence_depth(parsed)
    maturity = infer_ai_maturity(depth)
    assert maturity in (AIMaturity.NONE, AIMaturity.AWARENESS, AIMaturity.PILOT)
    assert maturity not in (
        AIMaturity.TRANSFORMATION_LEAD,
        AIMaturity.ENTERPRISE_AI_OWNER,
    )


def test_sivakumar_style_expected_ranking(engine: CareerIdentityEngine) -> None:
    scores = _proximity_map(engine, RESUME_SIVAKUMAR_STYLE)

    strong = {
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.ENTERPRISE_DELIVERY,
    }
    low = {
        RoleFamilyId.AI_GOVERNANCE,
        RoleFamilyId.OPERATIONS,
        RoleFamilyId.PRODUCT_MANAGEMENT,
        RoleFamilyId.HR,
        RoleFamilyId.SALES,
        RoleFamilyId.FINANCE,
    }

    strong_min = min(scores[f] for f in strong)
    assert scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT] >= strong_min - 0.05

    for family in low:
        assert scores[family] < strong_min + 0.08, (
            f"{family.value} too high: {scores[family]:.3f} vs strong_min {strong_min:.3f}"
        )

    assert scores[RoleFamilyId.AI_TRANSFORMATION] < scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT]
    assert scores[RoleFamilyId.AI_GOVERNANCE] < scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT]


def test_enterprise_leadership_cluster_spread(engine: CareerIdentityEngine) -> None:
    scores = _proximity_map(engine, RESUME_PROGRAM_DIRECTOR)
    cluster = [
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.AI_TRANSFORMATION,
        RoleFamilyId.ENTERPRISE_DELIVERY,
        RoleFamilyId.TRANSFORMATION_OFFICE,
        RoleFamilyId.OPERATIONS,
    ]
    proximities = [scores[f] for f in cluster]
    assert max(proximities) - min(proximities) >= 0.06


def test_ai_maturity_tiers_deterministic() -> None:
    parsed = ResumeParser().parse_text(RESUME_AI_TRANSFORMATION_LEAD)
    depth = analyze_evidence_depth(parsed)
    a = infer_ai_maturity(depth)
    b = infer_ai_maturity(depth)
    assert a == b
    assert a in (AIMaturity.TRANSFORMATION_LEAD, AIMaturity.ENTERPRISE_AI_OWNER)
