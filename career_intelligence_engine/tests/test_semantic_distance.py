"""Calibration tests for ontology-driven semantic distance."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.semantic_distance import compute_family_distance
from career_intelligence_engine.models.ontology import RoleFamilyId


def test_hr_far_from_ai_transformation() -> None:
    dist = compute_family_distance(
        RoleFamilyId.AI_TRANSFORMATION, RoleFamilyId.HR
    )
    assert dist > 0.8


def test_software_engineering_far_from_program_leadership() -> None:
    dist = compute_family_distance(
        RoleFamilyId.PROGRAM_LEADERSHIP, RoleFamilyId.SOFTWARE_ENGINEERING
    )
    assert dist > 0.7


def test_program_leadership_moderate_close_to_ai_transformation() -> None:
    dist = compute_family_distance(
        RoleFamilyId.PROGRAM_LEADERSHIP, RoleFamilyId.AI_TRANSFORMATION
    )
    assert 0.4 <= dist <= 0.7


def test_tpm_close_to_program_leadership() -> None:
    dist = compute_family_distance(
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT, RoleFamilyId.PROGRAM_LEADERSHIP
    )
    assert dist < 0.45


def test_tpm_moderate_from_product_management() -> None:
    dist = compute_family_distance(
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT, RoleFamilyId.PRODUCT_MANAGEMENT
    )
    assert 0.35 <= dist <= 0.75


def test_tpm_moderate_close_to_ai_transformation() -> None:
    dist = compute_family_distance(
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT, RoleFamilyId.AI_TRANSFORMATION
    )
    assert 0.35 <= dist <= 0.70


def test_same_family_zero_distance() -> None:
    assert compute_family_distance(
        RoleFamilyId.PROGRAM_LEADERSHIP, RoleFamilyId.PROGRAM_LEADERSHIP
    ) == 0.0


def test_enterprise_delivery_separated_from_program_leadership() -> None:
    dist = compute_family_distance(
        RoleFamilyId.ENTERPRISE_DELIVERY, RoleFamilyId.PROGRAM_LEADERSHIP
    )
    assert dist >= 0.18
    assert dist <= 0.55


def test_hr_extremely_far_from_tpm() -> None:
    dist = compute_family_distance(RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT, RoleFamilyId.HR)
    assert dist > 0.8


def test_deterministic_semantic_distance() -> None:
    a = compute_family_distance(RoleFamilyId.AI_TRANSFORMATION, RoleFamilyId.HR)
    b = compute_family_distance(RoleFamilyId.AI_TRANSFORMATION, RoleFamilyId.HR)
    assert a == b
