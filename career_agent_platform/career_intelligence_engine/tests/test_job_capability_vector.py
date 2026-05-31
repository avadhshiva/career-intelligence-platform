"""Tests for job capability vector generation."""

from __future__ import annotations

import math

import pytest

from career_intelligence_engine.intelligence.job_capability_vector import extract_job_vector
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.capability_vectors import CAPABILITY_DIMENSIONS


def test_job_vector_same_dimensions_as_candidate() -> None:
    result = extract_job_vector(
        corpus="release train sdlc governance architecture review",
        title="Technical Program Manager",
        job_hints={"primary_role_family": RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT},
    )
    assert set(result.vector.keys()) == set(CAPABILITY_DIMENSIONS)


def test_job_vector_normalized() -> None:
    result = extract_job_vector(
        corpus="product roadmap customer discovery go-to-market product strategy",
        title="Product Manager",
    )
    norm = math.sqrt(sum(v * v for v in result.vector.values()))
    assert norm == pytest.approx(1.0, abs=0.02) or norm == pytest.approx(0.0, abs=0.01)


def test_product_gate_boosts_product_thinking() -> None:
    result = extract_job_vector(
        corpus="delivery agile stakeholder",
        job_hints={"product_ownership_required": 0.85},
    )
    assert result.raw_scores["product_thinking"] >= 0.55
