"""Tests for deterministic score tracing and calibration gate fix."""

from __future__ import annotations

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_SIVAKUMAR_STYLE


def test_score_trace_populated() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_SIVAKUMAR_STYLE)
    trace = profile.explanations.get("score_trace")
    assert isinstance(trace, list)
    assert len(trace) == 20
    assert profile.explanations.get("scorer_path") == "canonical_unified_pipeline"


def test_sivakumar_trace_shows_product_penalties() -> None:
    profile = CareerIdentityEngine().analyze_text(RESUME_SIVAKUMAR_STYLE)
    by_family = {row["role_family"]: row for row in profile.explanations["score_trace"]}

    pd = by_family["product_delivery"]
    assert pd["primary_track_eligible"] is False
    assert any("penalty" in p.lower() or "reduced" in p.lower() for p in pd.get("penalties", []))

    ops = by_family["operations"]
    assert ops["adjacency_eligible"] is False
    assert ops["final_score"] < by_family["technical_program_management"]["final_score"]

    assert profile.primary_career_track != RoleFamilyId.PRODUCT_DELIVERY
    assert RoleFamilyId.OPERATIONS not in profile.adjacent_role_families


def test_identity_penalty_uses_product_ownership_depth() -> None:
    from career_intelligence_engine.ontology.role_family_calibration import (
        CalibrationContext,
        apply_identity_score_calibration,
    )

    ctx = CalibrationContext(
        raw_scores={"product_thinking": 0.35, "operational_management": 0.0},
        product_ownership_depth=0.10,
        operational_run_depth=0.0,
    )
    scores = {RoleFamilyId.PRODUCT_DELIVERY: 40.0}
    adjusted, penalties = apply_identity_score_calibration(scores, ctx)
    assert penalties
    assert adjusted[RoleFamilyId.PRODUCT_DELIVERY] < 40.0
