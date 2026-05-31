"""Aggregate benchmark metrics for ontology calibration."""

from __future__ import annotations

from dataclasses import dataclass, field

from career_intelligence_engine.benchmarks.contamination import ContaminationFinding
from career_intelligence_engine.benchmarks.drift import DriftWarning
from career_intelligence_engine.benchmarks.evaluator import FixtureEvaluationResult


@dataclass
class BenchmarkMetricsSummary:
    """Explainable aggregate metrics across all benchmark fixtures."""

    fixture_count: int = 0
    primary_correct: int = 0
    adjacency_hits: int = 0
    adjacency_expected: int = 0
    forbidden_top3_violations: int = 0
    forbidden_checks: int = 0
    excluded_zero_pass: int = 0
    excluded_checks: int = 0
    capability_trait_pass: int = 0
    capability_trait_checks: int = 0
    contamination_warnings: list[ContaminationFinding] = field(default_factory=list)
    drift_warnings: list[DriftWarning] = field(default_factory=list)
    fixture_results: list[FixtureEvaluationResult] = field(default_factory=list)

    @property
    def primary_accuracy(self) -> float:
        if self.fixture_count == 0:
            return 0.0
        return self.primary_correct / self.fixture_count

    @property
    def adjacency_accuracy(self) -> float:
        if self.adjacency_expected == 0:
            return 1.0
        return self.adjacency_hits / self.adjacency_expected

    @property
    def false_positive_rate(self) -> float:
        if self.forbidden_checks == 0:
            return 0.0
        return self.forbidden_top3_violations / self.forbidden_checks

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.fixture_results)

    def to_dict(self) -> dict[str, object]:
        return {
            "fixture_count": self.fixture_count,
            "primary_accuracy": round(self.primary_accuracy, 4),
            "adjacency_accuracy": round(self.adjacency_accuracy, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "contamination_warning_count": len(
                [c for c in self.contamination_warnings if c.is_contaminated]
            ),
            "drift_warning_count": len(self.drift_warnings),
            "all_passed": self.all_passed,
        }

    @classmethod
    def from_results(
        cls,
        results: list[FixtureEvaluationResult],
        contamination: list[ContaminationFinding],
        drift: list[DriftWarning],
    ) -> BenchmarkMetricsSummary:
        summary = cls(
            fixture_count=len(results),
            contamination_warnings=contamination,
            drift_warnings=drift,
            fixture_results=results,
        )
        for r in results:
            if r.primary_correct:
                summary.primary_correct += 1
            summary.adjacency_hits += r.adjacency_hits
            summary.adjacency_expected += r.adjacency_expected
            summary.forbidden_top3_violations += r.forbidden_top3_violations
            summary.forbidden_checks += r.forbidden_checks
            summary.excluded_zero_pass += r.excluded_zero_pass
            summary.excluded_checks += r.excluded_checks
            summary.capability_trait_pass += r.capability_trait_pass
            summary.capability_trait_checks += r.capability_trait_checks
        return summary
