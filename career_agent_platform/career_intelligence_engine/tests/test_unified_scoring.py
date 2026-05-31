"""Tests for unified role-family scoring architecture."""

from __future__ import annotations

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer
from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_SIVAKUMAR_STYLE


def test_identity_and_proximity_ranking_aligned() -> None:
    """Primary, ranking, and proximity table must share the same final_score ordering."""
    profile = CareerIdentityEngine().analyze_text(RESUME_SIVAKUMAR_STYLE)
    ranked = CareerDistanceScorer().rank_role_families(profile)
    proximity_order = [fid for fid, _ in ranked]

    exp_ranking = [
        RoleFamilyId(row["family"]) for row in profile.explanations["role_family_ranking"]
    ]
    assert exp_ranking == proximity_order[: len(exp_ranking)]
    assert profile.primary_career_track == proximity_order[0]


def test_operations_zero_gate_blocks_adjacency_and_low_final() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_SIVAKUMAR_STYLE)
    by_family = {row["role_family"]: row for row in profile.explanations["score_trace"]}
    ops = by_family["operations"]
    tpm = by_family["technical_program_management"]

    assert ops["adjacency_eligible"] is False
    assert ops["final_score"] < tpm["final_score"]
    assert RoleFamilyId.OPERATIONS not in profile.adjacent_role_families
    assert all(
        row.get("scorer_path") == "canonical_unified_pipeline"
        for row in profile.explanations["score_trace"]
    )
    assert profile.explanations.get("scorer_path") == "canonical_unified_pipeline"
    assert profile.explanations["canonical_ranking"]["scorer_path"] == "canonical_unified_pipeline"
