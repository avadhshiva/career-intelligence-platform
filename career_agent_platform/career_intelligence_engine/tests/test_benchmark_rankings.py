"""Benchmark ranking tests — deterministic ontology calibration guardrails."""

from __future__ import annotations

import pytest

from career_intelligence_engine.benchmarks.contamination import (
    CONTAMINATION_RULES,
    detect_contamination,
)
from career_intelligence_engine.benchmarks.evaluator import BenchmarkEvaluator
from career_intelligence_engine.benchmarks.metrics import BenchmarkMetricsSummary
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes import (
    ALL_BENCHMARK_FIXTURES,
    BENCHMARK_FIXTURE_BY_ID,
)


@pytest.fixture
def evaluator() -> BenchmarkEvaluator:
    return BenchmarkEvaluator()


@pytest.mark.parametrize(
    "fixture_id",
    [f.fixture_id for f in ALL_BENCHMARK_FIXTURES],
)
def test_benchmark_fixture_passes(evaluator: BenchmarkEvaluator, fixture_id: str) -> None:
    fixture = BENCHMARK_FIXTURE_BY_ID[fixture_id]
    result = evaluator.evaluate_fixture(fixture, check_drift=False)
    assert result.passed, result.failure_summary()


def test_benchmark_suite_aggregate_metrics(evaluator: BenchmarkEvaluator) -> None:
    run = evaluator.evaluate_all(check_drift=False)
    summary = BenchmarkMetricsSummary.from_results(
        run.results, run.contamination, run.drift_warnings
    )
    assert summary.fixture_count == len(ALL_BENCHMARK_FIXTURES)
    assert summary.primary_accuracy == 1.0
    assert summary.false_positive_rate == 0.0
    assert summary.all_passed


def test_tpm_excludes_product_and_ops_from_ranking(evaluator: BenchmarkEvaluator) -> None:
    fixture = BENCHMARK_FIXTURE_BY_ID["technical_program_manager_enterprise"]
    result = evaluator.evaluate_fixture(fixture, check_drift=False)
    profile = evaluator._engine.analyze_text(fixture.resume_text)
    trace = {r["role_family"]: r for r in profile.explanations["score_trace"]}
    for fam in ("product_delivery", "product_management", "operations"):
        assert trace[fam]["final_score"] == 0.0
    assert RoleFamilyId.PRODUCT_DELIVERY not in {
        fid for fid, _ in result.top_ranked[:3]
    }


def test_contamination_rules_cover_required_pairs() -> None:
    fixtures = {rule[0] for rule in CONTAMINATION_RULES}
    assert "technical_program_manager_enterprise" in fixtures
    assert "program_leadership_enterprise" in fixtures
    assert "ai_transformation_director" in fixtures
    assert "enterprise_architect" in fixtures


def test_score_drift_detects_large_changes() -> None:
    from career_intelligence_engine.benchmarks.drift import detect_drift, load_baseline

    baseline = load_baseline()
    if not baseline:
        pytest.skip("baseline_scores.json not generated yet")
    fixture_id = "technical_program_manager_enterprise"
    current = {
        fam: dict(scores)
        for fam, scores in baseline[fixture_id].items()
    }
    current["technical_program_management"]["final_score"] *= 1.5
    warnings = detect_drift(fixture_id, current, baseline)
    assert warnings


def test_contamination_detector_is_deterministic() -> None:
    ranked = [
        (RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT, 0.85),
        (RoleFamilyId.PRODUCT_DELIVERY, 0.70),
        (RoleFamilyId.RELEASE_GOVERNANCE, 0.65),
    ]
    findings = detect_contamination(
        "technical_program_manager_enterprise",
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        ranked,
    )
    assert findings
    assert any(f.is_contaminated for f in findings)
