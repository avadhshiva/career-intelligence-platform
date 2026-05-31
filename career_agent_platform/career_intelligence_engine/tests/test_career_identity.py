"""Tests for senior program manager / AI transformation career path."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.models.ontology import RoleFamilyId
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

Program Manager | Consulting Firm | 2009 – 2013
• ERP and CRM implementation, change management

SKILLS
Program management, PMP, agile, AI strategy, GenAI, responsible AI, governance, AWS
"""


@pytest.fixture
def engine() -> CareerIdentityEngine:
    return CareerIdentityEngine()


@pytest.fixture
def profile(engine: CareerIdentityEngine):
    return engine.analyze_text(SAMPLE_RESUME)


def test_primary_track_is_program_or_tpm(profile) -> None:
    assert profile.primary_career_track in (
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.AI_TRANSFORMATION,
        RoleFamilyId.ENTERPRISE_DELIVERY,
    )


def test_adjacent_includes_transformation_families(profile) -> None:
    adjacent = set(profile.adjacent_role_families)
    # Should include at least one delivery/AI adjacent family
    expected_any = {
        RoleFamilyId.AI_TRANSFORMATION,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.ENTERPRISE_DELIVERY,
        RoleFamilyId.PROGRAM_LEADERSHIP,
    }
    assert adjacent & expected_any or profile.primary_career_track in expected_any


def test_hr_and_sales_are_far(profile) -> None:
    scorer = CareerDistanceScorer()
    ranked = scorer.rank_role_families(profile)
    families = [fid for fid, _ in ranked]
    hr_idx = families.index(RoleFamilyId.HR)
    sales_idx = families.index(RoleFamilyId.SALES)
    tpm_idx = families.index(RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT)
    assert hr_idx > tpm_idx
    assert sales_idx > tpm_idx


def test_transformation_focus_nonzero(profile) -> None:
    assert profile.transformation_focus >= 0.2


def test_explanations_present(profile) -> None:
    assert "primary_career_track" in profile.explanations
    assert "role_family_ranking" in profile.explanations


def test_career_distance_same_family_zero() -> None:
    from career_intelligence_engine.models.ontology import (
        CareerDistanceInput,
        EnterpriseExposure,
        LeadershipLevel,
        SeniorityLevel,
    )

    scorer = CareerDistanceScorer()
    inp = CareerDistanceInput(
        source_role_family=RoleFamilyId.PROGRAM_LEADERSHIP,
        target_role_family=RoleFamilyId.PROGRAM_LEADERSHIP,
        source_seniority=SeniorityLevel.SENIOR,
        target_seniority=SeniorityLevel.SENIOR,
        source_leadership=LeadershipLevel.ORG_LEADER,
        target_leadership=LeadershipLevel.ORG_LEADER,
        source_domains=["Program & Portfolio Management"],
        target_domains=["Program & Portfolio Management"],
        source_enterprise=EnterpriseExposure.DEEP,
        target_enterprise=EnterpriseExposure.DEEP,
        source_transformation=0.8,
        target_transformation=0.8,
    )
    result = scorer.score(inp)
    assert result.distance < 0.15
    assert result.proximity > 0.85
