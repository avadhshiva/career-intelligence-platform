"""Real-world benchmark evaluator — production evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass, field

from career_intelligence_engine.benchmarks.drift import detect_drift, load_baseline
from career_intelligence_engine.benchmarks.real_world.schema import BenchmarkFixture
from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.contamination_analysis import (
    analyze_contamination,
)
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer


@dataclass
class RealWorldFixtureResult:
    fixture_id: str
    passed: bool
    expected_primary: str
    actual_primary: str
    primary_correct: bool
    adjacency_precision: float
    contamination_detected: bool
    exclusion_correct: bool
    confidence_score: float
    confidence_meets_minimum: bool
    failures: list[str] = field(default_factory=list)
    drift_warnings: list[str] = field(default_factory=list)
    contamination_families: list[str] = field(default_factory=list)


@dataclass
class RealWorldBenchmarkSummary:
    fixture_count: int
    primary_accuracy: float
    adjacency_precision: float
    contamination_rate: float
    exclusion_correctness: float
    confidence_calibration: float
    drift_warning_count: int
    all_passed: bool
    fixture_results: list[RealWorldFixtureResult] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)


class RealWorldBenchmarkEvaluator:
    def __init__(self, engine: CareerIdentityEngine | None = None) -> None:
        self._engine = engine or CareerIdentityEngine()
        self._scorer = CareerDistanceScorer()

    def evaluate_fixture(
        self,
        fixture: BenchmarkFixture,
        *,
        check_drift: bool = True,
    ) -> RealWorldFixtureResult:
        profile = self._engine.analyze_text(fixture.resume_text)
        ranked = self._scorer.rank_role_families(profile)
        score_trace = {
            row["role_family"]: row
            for row in profile.explanations.get("score_trace", [])
        }
        actual_primary = profile.primary_career_track.value
        expected = fixture.expected_primary
        allowed_primaries = {expected} | set(fixture.acceptable_primaries)
        primary_correct = actual_primary in allowed_primaries

        failures: list[str] = []
        if not primary_correct:
            failures.append(
                f"primary: expected one of {sorted(allowed_primaries)}, got {actual_primary}"
            )

        top3 = {fid.value for fid, _ in ranked[:3]}
        forbidden_hits = [f for f in fixture.forbidden_families if f in top3]
        if forbidden_hits:
            failures.append(f"forbidden in top3: {forbidden_hits}")

        exclusion_ok = True
        for excluded in fixture.expected_exclusions:
            row = score_trace.get(excluded, {})
            final = float(row.get("final_score", -1))
            if final != 0.0:
                exclusion_ok = False
                failures.append(f"exclusion {excluded}: final_score={final}")

        adjacent_set = {a.value for a in profile.adjacent_role_families}
        allowed = set(fixture.allowed_adjacent)
        if allowed:
            hits = len(adjacent_set & allowed)
            adj_precision = hits / len(allowed)
            if hits == 0 and allowed:
                failures.append(f"adjacency: none of {sorted(allowed)} in adjacent")
        else:
            adj_precision = 1.0

        contamination_signals = analyze_contamination(profile)
        contamination_detected = len(contamination_signals) > 0

        conf = profile.confidence_result
        conf_score = conf.confidence_score if conf else 0.0
        conf_ok = conf_score >= fixture.minimum_confidence
        if fixture.minimum_confidence > 0 and not conf_ok:
            failures.append(
                f"confidence {conf_score:.3f} < minimum {fixture.minimum_confidence}"
            )

        drift_warnings: list[str] = []
        if check_drift:
            snapshot = {
                fam: {
                    "ontology_score": float(row.get("ontology_score", 0)),
                    "final_score": float(row.get("final_score", 0)),
                }
                for fam, row in score_trace.items()
            }
            baseline = load_baseline()
            for w in detect_drift(fixture.fixture_id, snapshot, baseline):
                drift_warnings.append(w.message)

        return RealWorldFixtureResult(
            fixture_id=fixture.fixture_id,
            passed=len(failures) == 0,
            expected_primary=expected,
            actual_primary=actual_primary,
            primary_correct=primary_correct,
            adjacency_precision=round(adj_precision, 4),
            contamination_detected=contamination_detected,
            exclusion_correct=exclusion_ok,
            confidence_score=round(conf_score, 4),
            confidence_meets_minimum=conf_ok,
            failures=failures,
            drift_warnings=drift_warnings,
            contamination_families=[s.family for s in contamination_signals],
        )

    def evaluate_all(
        self,
        fixtures: tuple[BenchmarkFixture, ...],
        *,
        check_drift: bool = True,
    ) -> RealWorldBenchmarkSummary:
        results = [
            self.evaluate_fixture(f, check_drift=check_drift) for f in fixtures
        ]
        n = len(results) or 1
        return RealWorldBenchmarkSummary(
            fixture_count=len(results),
            primary_accuracy=sum(1 for r in results if r.primary_correct) / n,
            adjacency_precision=sum(r.adjacency_precision for r in results) / n,
            contamination_rate=sum(1 for r in results if r.contamination_detected) / n,
            exclusion_correctness=sum(1 for r in results if r.exclusion_correct) / n,
            confidence_calibration=sum(
                1 for r in results if r.confidence_meets_minimum
            )
            / n,
            drift_warning_count=sum(len(r.drift_warnings) for r in results),
            all_passed=all(r.passed for r in results),
            fixture_results=results,
        )
