"""Two-stage ranking: eligibility filtering before sort."""

from __future__ import annotations

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer
from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_SIVAKUMAR_STYLE

_PROGRAM_CLUSTER = frozenset(
    {
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.ENTERPRISE_DELIVERY,
        RoleFamilyId.AI_PROGRAM_MANAGEMENT,
    }
)

_LOW_FAMILIES = frozenset(
    {
        RoleFamilyId.PRODUCT_DELIVERY,
        RoleFamilyId.PRODUCT_MANAGEMENT,
        RoleFamilyId.OPERATIONS,
        RoleFamilyId.ENTERPRISE_OPERATIONS,
    }
)


def test_ineligible_families_excluded_from_ranking_pool() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_SIVAKUMAR_STYLE)
    matrix = profile.explanations["eligibility_matrix"]
    excluded = set(profile.explanations["excluded_from_ranking"])

    assert "product_delivery" in excluded
    assert "product_management" in excluded
    assert "operations" in excluded
    assert "enterprise_operations" in excluded

    for fid in _LOW_FAMILIES:
        row = matrix[fid.value]
        assert row["eligible_for_ranking"] is False
        assert row["eligible_for_primary"] is False
        assert row["eligible_for_adjacency"] is False


def test_primary_not_product_delivery_and_ops_not_adjacent() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_SIVAKUMAR_STYLE)
    assert profile.primary_career_track != RoleFamilyId.PRODUCT_DELIVERY
    assert profile.primary_career_track in _PROGRAM_CLUSTER
    assert RoleFamilyId.OPERATIONS not in profile.adjacent_role_families
    assert RoleFamilyId.ENTERPRISE_OPERATIONS not in profile.adjacent_role_families


def test_top_ranked_are_program_cluster() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_SIVAKUMAR_STYLE)
    ranked = CareerDistanceScorer().rank_role_families(profile)
    top_four = [fid for fid, _ in ranked[:4]]

    assert all(fid in _PROGRAM_CLUSTER for fid in top_four[:4])
    for low in _LOW_FAMILIES:
        row = next(r for fid, r in ranked if fid == low)
        assert row.proximity == 0.0
