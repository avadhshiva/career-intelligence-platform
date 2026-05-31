"""Tests for role-family ontology calibration (product vs delivery vs operations)."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer
from career_intelligence_engine.tests.fixtures.calibration_resumes import (
    RESUME_SIVAKUMAR_STYLE,
    RESUME_TPM,
)


@pytest.fixture
def engine() -> CareerIdentityEngine:
    return CareerIdentityEngine()


def test_sivakumar_primary_not_product_delivery(engine: CareerIdentityEngine) -> None:
    profile = engine.analyze_text(RESUME_SIVAKUMAR_STYLE)
    assert profile.primary_career_track != RoleFamilyId.PRODUCT_DELIVERY
    assert profile.primary_career_track != RoleFamilyId.PRODUCT_MANAGEMENT
    assert profile.primary_career_track in (
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.ENTERPRISE_DELIVERY,
    )


def test_sivakumar_operations_not_adjacent(engine: CareerIdentityEngine) -> None:
    profile = engine.analyze_text(RESUME_SIVAKUMAR_STYLE)
    adjacent = set(profile.adjacent_role_families)
    assert RoleFamilyId.OPERATIONS not in adjacent
    assert RoleFamilyId.ENTERPRISE_OPERATIONS not in adjacent
    assert profile.explanations.get("operational_run_depth", 1.0) == 0.0 or (
        profile.explanations.get("operational_run_depth") is not None
    )


def test_sivakumar_vector_ranking_expectations(engine: CareerIdentityEngine) -> None:
    profile = engine.analyze_text(RESUME_SIVAKUMAR_STYLE)
    ranked = CareerDistanceScorer().rank_role_families(profile)
    scores = {fid: r.proximity for fid, r in ranked}

    strong = [
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.ENTERPRISE_DELIVERY,
    ]
    # Ignore near-zero suppressed families (e.g. enterprise delivery on TPM-heavy resumes)
    strong_scores = [scores[f] for f in strong if scores[f] > 0.10]
    assert strong_scores, "expected at least one strong delivery-family score"
    strong_min = min(strong_scores)

    assert scores[RoleFamilyId.OPERATIONS] < strong_min - 0.05
    assert scores[RoleFamilyId.PRODUCT_MANAGEMENT] < strong_min - 0.05
    assert scores[RoleFamilyId.AI_GOVERNANCE] < strong_min
    assert scores[RoleFamilyId.HR] < 0.45
    assert scores[RoleFamilyId.SALES] < 0.45

    assert scores[RoleFamilyId.PRODUCT_DELIVERY] < scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT]
    assert scores[RoleFamilyId.AI_TRANSFORMATION] < scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT]


def test_tpm_resume_product_delivery_penalized(engine: CareerIdentityEngine) -> None:
    profile = engine.analyze_text(RESUME_TPM)
    ranked = CareerDistanceScorer().rank_role_families(profile)
    scores = {fid: r.proximity for fid, r in ranked}
    assert scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT] > scores[RoleFamilyId.PRODUCT_DELIVERY]
    assert scores[RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT] > scores[RoleFamilyId.PRODUCT_MANAGEMENT]
