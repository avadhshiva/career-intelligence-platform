"""Tests for capability-aware role-family distance and explainability."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.career_distance import (
    calculate_role_family_distance,
    rank_role_families_by_fit,
)
from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.explainability import (
    generate_structured_explanations,
)
from career_intelligence_engine.models.ontology import RoleFamilyId

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

Program Manager | Consulting Firm | 2009 – 2013
• ERP and CRM implementation, change management

SKILLS
Program management, PMP, agile, AI strategy, GenAI, responsible AI, governance, AWS
"""


@pytest.fixture
def profile():
    return CareerIdentityEngine().analyze_text(SAMPLE_RESUME)


def test_program_leadership_closer_than_hr(profile) -> None:
    prog = calculate_role_family_distance(profile, RoleFamilyId.PROGRAM_LEADERSHIP)
    hr = calculate_role_family_distance(profile, RoleFamilyId.HR)
    assert prog["score"] > hr["score"]
    assert prog["distance"] < hr["distance"]


def test_unrelated_family_rejection(profile) -> None:
    sales = calculate_role_family_distance(profile, RoleFamilyId.SALES)
    finance = calculate_role_family_distance(profile, RoleFamilyId.FINANCE)
    prog = calculate_role_family_distance(profile, RoleFamilyId.PROGRAM_LEADERSHIP)
    assert sales["score"] < prog["score"]
    assert finance["score"] < prog["score"]


def test_distance_is_one_minus_score(profile) -> None:
    result = calculate_role_family_distance(
        profile, RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT
    )
    assert result["distance"] == pytest.approx(1.0 - result["score"], abs=1e-3)


def test_explanations_are_structured(profile) -> None:
    result = calculate_role_family_distance(profile, RoleFamilyId.PROGRAM_LEADERSHIP)
    assert len(result["explanations"]) >= 4
    assert all(isinstance(e, str) for e in result["explanations"])


def test_ranking_prefers_enterprise_tracks(profile) -> None:
    ranked = rank_role_families_by_fit(profile)
    top_five = [fid for fid, _ in ranked[:5]]
    enterprise_tracks = {
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.AI_TRANSFORMATION,
        RoleFamilyId.AI_PROGRAM_MANAGEMENT,
        RoleFamilyId.ENTERPRISE_DELIVERY,
        RoleFamilyId.TRANSFORMATION_OFFICE,
    }
    assert enterprise_tracks & set(top_five)


def test_explainability_no_empty_primary_reasons(profile) -> None:
    explanations = generate_structured_explanations(profile)
    primary_key = f"why_{profile.primary_career_track.value}"
    assert primary_key in explanations
    reasons = explanations[primary_key]
    assert isinstance(reasons, list)
    assert len(reasons) >= 1
    assert all(len(r) > 10 for r in reasons)


def test_explainability_transformation_and_leadership(profile) -> None:
    explanations = generate_structured_explanations(profile)
    assert "transformation_focus" in explanations
    assert "leadership_inference" in explanations
    assert "enterprise_exposure" in explanations


def test_deterministic_distance_repeatability(profile) -> None:
    a = calculate_role_family_distance(profile, RoleFamilyId.PROGRAM_LEADERSHIP)
    b = calculate_role_family_distance(profile, RoleFamilyId.PROGRAM_LEADERSHIP)
    assert a == b
