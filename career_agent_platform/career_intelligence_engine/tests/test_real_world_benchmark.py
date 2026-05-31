"""Tests for real-world benchmark framework."""

from __future__ import annotations

import pytest

from career_intelligence_engine.benchmarks.real_world.evaluator import (
    RealWorldBenchmarkEvaluator,
)
from career_intelligence_engine.benchmarks.real_world.loader import load_all_fixtures
from career_intelligence_engine.benchmarks.real_world.schema import BenchmarkFixture


@pytest.fixture(scope="module", autouse=True)
def ensure_fixtures_exist() -> None:
    fixtures = load_all_fixtures()
    if not fixtures:
        from career_intelligence_engine.benchmarks.real_world.generate_fixtures import (
            generate,
        )

        generate()


def test_fixtures_loaded() -> None:
    fixtures = load_all_fixtures()
    assert len(fixtures) >= 20


def test_fixture_schema_validation() -> None:
    fixture = BenchmarkFixture(
        fixture_id="test_fixture",
        resume_text="Sample resume text for testing.",
        expected_primary="technical_program_management",
        allowed_adjacent=["program_leadership"],
        forbidden_families=["hr"],
        expected_exclusions=["operations"],
        minimum_confidence=0.2,
    )
    assert fixture.fixture_id == "test_fixture"


def test_real_world_suite_passes() -> None:
    fixtures = load_all_fixtures()
    evaluator = RealWorldBenchmarkEvaluator()
    summary = evaluator.evaluate_all(fixtures, check_drift=False)
    assert summary.fixture_count >= 20
    assert summary.primary_accuracy >= 0.85


def test_real_world_evaluator_runs() -> None:
    fixtures = load_all_fixtures()
    evaluator = RealWorldBenchmarkEvaluator()
    summary = evaluator.evaluate_all(fixtures[:3], check_drift=False)
    assert summary.fixture_count == 3
    assert 0.0 <= summary.primary_accuracy <= 1.0
