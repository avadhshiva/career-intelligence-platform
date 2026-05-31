"""Tests for deterministic job description parsing."""

from __future__ import annotations

import math

import pytest

from career_intelligence_engine.intelligence.job_parser import parse_job_description
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.capability_vectors import CAPABILITY_DIMENSIONS
from career_intelligence_engine.tests.fixtures.sample_jds import (
    JD_AI_TRANSFORMATION,
    JD_OPERATIONS,
    JD_PRODUCT,
    JD_RELEASE_GOVERNANCE,
    JD_TPM,
)


def test_job_parser_tpm_role_family() -> None:
    job = parse_job_description(JD_TPM)
    assert job.primary_role_family in (
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.PROGRAM_LEADERSHIP,
    )
    assert job.is_release_governance_heavy or job.capability_raw_scores.get(
        "release_governance", 0
    ) > 0


def test_job_parser_product_flags() -> None:
    job = parse_job_description(JD_PRODUCT)
    assert job.is_product_heavy
    assert job.product_ownership_required >= 0.35


def test_job_parser_operations_flags() -> None:
    job = parse_job_description(JD_OPERATIONS)
    assert job.is_operations_heavy
    assert job.operational_ownership_required >= 0.35


def test_job_parser_ai_transformation() -> None:
    job = parse_job_description(JD_AI_TRANSFORMATION)
    assert job.is_ai_transformation
    assert job.transformation_type in ("ai", "operating_model", "none")


def test_job_vector_l2_normalized() -> None:
    job = parse_job_description(JD_RELEASE_GOVERNANCE)
    norm = math.sqrt(
        sum(job.capability_vector.get(d, 0.0) ** 2 for d in CAPABILITY_DIMENSIONS)
    )
    assert norm == pytest.approx(0.0, abs=0.01) or norm == pytest.approx(1.0, abs=0.02)


def test_job_parser_deterministic() -> None:
    a = parse_job_description(JD_TPM)
    b = parse_job_description(JD_TPM)
    assert a.primary_role_family == b.primary_role_family
    assert a.capability_vector == b.capability_vector
