"""Tests for capability-vector proximity and role-family differentiation."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.vector_proximity import (
    rank_role_families_by_vector,
    score_vector_proximity,
)
from career_intelligence_engine.intelligence.candidate_vector import extract_candidate_vector
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.capability_vectors import (
    cosine_similarity,
    get_role_family_vector,
)
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer

SAMPLE_RESUME = """
Jordan Lee
jordan.lee@email.com | Austin, TX

EXPERIENCE
Senior Program Manager | Enterprise Corp | 2018 – Present
• Enterprise AI transformation and program governance across global matrix
• Executive stakeholder management and steering committee facilitation
• Technical program coordination with engineering and MLOps teams
• Fortune 500 client delivery and multi-region rollout

Technical Program Manager | Tech Vendor | 2013 – 2018
• Release train, SDLC, dependency management, cloud migration
• Architecture reviews and CI/CD adoption across product teams

Program Manager | Consulting Firm | 2009 – 2013
• ERP and CRM implementation, change management

SKILLS
Program management, PMP, agile, AI strategy, GenAI, responsible AI, governance, AWS
"""


@pytest.fixture
def profile():
    return CareerIdentityEngine().analyze_text(SAMPLE_RESUME)


def test_role_family_vectors_are_distinct() -> None:
    tpm = get_role_family_vector(RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT)
    ai = get_role_family_vector(RoleFamilyId.AI_TRANSFORMATION)
    ops = get_role_family_vector(RoleFamilyId.OPERATIONS)
    assert cosine_similarity(tpm, ai) < 0.85
    assert cosine_similarity(tpm, ops) < 0.75
    assert cosine_similarity(ai, ops) < 0.70


def test_candidate_vector_normalized(profile) -> None:
    cv = extract_candidate_vector(profile)
    norm = sum(v * v for v in cv.vector.values()) ** 0.5
    assert norm == pytest.approx(1.0, abs=0.02)
    assert cv.raw_scores.get("ai_strategy", 0) > 0.2


def test_enterprise_families_not_clustered(profile) -> None:
    ranked = rank_role_families_by_vector(profile)
    scores = {fid: r.proximity for fid, r in ranked}

    leadership_families = [
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.AI_TRANSFORMATION,
        RoleFamilyId.ENTERPRISE_DELIVERY,
        RoleFamilyId.TRANSFORMATION_OFFICE,
        RoleFamilyId.OPERATIONS,
    ]
    proximities = [scores[f] for f in leadership_families]
    spread = max(proximities) - min(proximities)
    assert spread >= 0.08, f"Families too clustered: {proximities}"


def test_tpm_beats_operations_for_tpm_resume(profile) -> None:
    ranked = rank_role_families_by_vector(profile)
    scores = {fid: r.proximity for fid, r in ranked}
    assert scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT] > scores[RoleFamilyId.OPERATIONS]
    assert scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT] > scores[RoleFamilyId.HR]


def test_operations_penalty_without_ops_evidence(profile) -> None:
    cv = extract_candidate_vector(profile)
    ops_result = score_vector_proximity(
        cv.vector, RoleFamilyId.OPERATIONS, raw_scores=cv.raw_scores
    )
    assert ops_result.penalty_applied > 0 or ops_result.proximity < 0.65


def test_vector_explanation_present(profile) -> None:
    cv = extract_candidate_vector(profile)
    result = score_vector_proximity(
        cv.vector,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        raw_scores=cv.raw_scores,
    )
    assert len(result.explanation) > 20
    assert result.dominant_dimensions


def test_scorer_ranking_has_dimension_columns(profile) -> None:
    ranked = CareerDistanceScorer().rank_role_families(profile)
    top = ranked[0][1]
    assert top.dominant_dimensions
    assert top.vector_explanation
    assert top.semantic_distance == pytest.approx(1.0 - top.proximity, abs=1e-3)


def test_hr_sales_far_from_top(profile) -> None:
    ranked = CareerDistanceScorer().rank_role_families(profile)
    families = [fid for fid, _ in ranked]
    top_five = set(families[:5])
    assert RoleFamilyId.HR not in top_five
    assert RoleFamilyId.SALES not in top_five
