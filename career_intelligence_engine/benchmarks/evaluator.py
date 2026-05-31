"""Run deterministic benchmark evaluations against fixture resumes."""

from __future__ import annotations

from dataclasses import dataclass, field

from career_intelligence_engine.benchmarks.contamination import (
    detect_contamination,
    ContaminationFinding,
)
from career_intelligence_engine.benchmarks.drift import detect_drift, DriftWarning, load_baseline
from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.semantic_distance import compute_family_distance
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer
from career_intelligence_engine.tests.benchmark_resumes import ALL_BENCHMARK_FIXTURES
from career_intelligence_engine.tests.benchmark_resumes.schema import BenchmarkResumeFixture

_SEMANTIC_ADJACENCY_MAX_DISTANCE = 0.72


@dataclass
class FixtureEvaluationResult:
    fixture_id: str
    passed: bool
    expected_primary: RoleFamilyId
    actual_primary: RoleFamilyId
    primary_correct: bool
    adjacency_hits: int = 0
    adjacency_expected: int = 0
    forbidden_top3_violations: int = 0
    forbidden_checks: int = 0
    excluded_zero_pass: int = 0
    excluded_checks: int = 0
    capability_trait_pass: int = 0
    capability_trait_checks: int = 0
    top_ranked: list[tuple[RoleFamilyId, float]] = field(default_factory=list)
    actual_adjacent: list[RoleFamilyId] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    contamination: list[ContaminationFinding] = field(default_factory=list)
    drift_warnings: list[DriftWarning] = field(default_factory=list)

    def failure_summary(self) -> str:
        return "; ".join(self.failures) if self.failures else "ok"


@dataclass
class BenchmarkRunResult:
    results: list[FixtureEvaluationResult]
    contamination: list[ContaminationFinding]
    drift_warnings: list[DriftWarning]

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


class BenchmarkEvaluator:
    """Evaluate benchmark fixtures through the canonical unified pipeline."""

    def __init__(self, engine: CareerIdentityEngine | None = None) -> None:
        self._engine = engine or CareerIdentityEngine()
        self._scorer = CareerDistanceScorer()

    def evaluate_fixture(
        self,
        fixture: BenchmarkResumeFixture,
        *,
        check_drift: bool = True,
    ) -> FixtureEvaluationResult:
        profile = self._engine.analyze_text(fixture.resume_text)
        ranked = self._scorer.rank_role_families(profile)
        top_ranked = [(fid, result.proximity) for fid, result in ranked[:10]]
        score_trace = {
            row["role_family"]: row
            for row in profile.explanations.get("score_trace", [])
        }

        result = FixtureEvaluationResult(
            fixture_id=fixture.fixture_id,
            passed=True,
            expected_primary=fixture.expected_primary,
            actual_primary=profile.primary_career_track,
            primary_correct=profile.primary_career_track == fixture.expected_primary,
            top_ranked=top_ranked,
            actual_adjacent=list(profile.adjacent_role_families),
        )

        allowed_primaries = (fixture.expected_primary,) + fixture.acceptable_primaries
        result.primary_correct = profile.primary_career_track in allowed_primaries
        if not result.primary_correct:
            result.passed = False
            allowed = ", ".join(f.value for f in allowed_primaries)
            result.failures.append(
                f"primary: expected one of [{allowed}], "
                f"got {profile.primary_career_track.value}"
            )

        top3 = {fid for fid, _ in top_ranked[:3]}
        for forbidden in fixture.forbidden_families:
            result.forbidden_checks += 1
            if forbidden in top3:
                result.forbidden_top3_violations += 1
                result.passed = False
                result.failures.append(
                    f"forbidden {forbidden.value} in top 3"
                )

        for excluded in fixture.excluded_families:
            result.excluded_checks += 1
            row = score_trace.get(excluded.value, {})
            final = float(row.get("final_score", -1))
            if final != 0.0:
                result.passed = False
                result.failures.append(
                    f"excluded {excluded.value} final_score={final}, expected 0"
                )
            else:
                result.excluded_zero_pass += 1

        result.adjacency_expected = len(fixture.expected_adjacent)
        adjacent_set = set(profile.adjacent_role_families)
        for expected in fixture.expected_adjacent:
            if expected in adjacent_set:
                result.adjacency_hits += 1
                continue
            dist = compute_family_distance(
                fixture.expected_primary, expected
            )
            if dist <= _SEMANTIC_ADJACENCY_MAX_DISTANCE and expected in {
                fid for fid, _ in top_ranked[:6]
            }:
                result.adjacency_hits += 1
            else:
                result.passed = False
                result.failures.append(
                    f"adjacency miss: {expected.value} "
                    f"(dist={dist:.2f}, in_adjacent={expected in adjacent_set})"
                )

        vector = profile.capability_vector or {}
        rank_by_family = {fid: rank for rank, (fid, _) in enumerate(top_ranked, 1)}
        for family, max_rank in fixture.must_rank_in_top:
            rank = rank_by_family.get(family, 99)
            if rank > max_rank:
                result.passed = False
                result.failures.append(
                    f"rank: {family.value} at position {rank}, expected top {max_rank}"
                )

        for trait in fixture.capability_traits:
            result.capability_trait_checks += 1
            value = float(vector.get(trait.dimension, 0.0))
            if trait.min_value <= value <= trait.max_value:
                result.capability_trait_pass += 1
            else:
                result.passed = False
                result.failures.append(
                    f"capability {trait.dimension}={value:.3f}, "
                    f"expected [{trait.min_value}, {trait.max_value}]"
                )

        ranked_scores = [(fid, float(score_trace.get(fid.value, {}).get("final_score", 0))) for fid, _ in ranked]
        result.contamination = detect_contamination(
            fixture.fixture_id,
            profile.primary_career_track,
            ranked_scores,
        )
        for finding in result.contamination:
            if finding.is_contaminated:
                result.passed = False
                result.failures.append(
                    f"contamination: {finding.cause} "
                    f"(rank={finding.contaminant_rank}, ratio={finding.score_ratio:.2f})"
                )

        if check_drift:
            current_snapshot = {
                fam: {
                    "ontology_score": float(row.get("ontology_score", 0)),
                    "final_score": float(row.get("final_score", 0)),
                }
                for fam, row in score_trace.items()
            }
            result.drift_warnings = detect_drift(
                fixture.fixture_id, current_snapshot, load_baseline()
            )

        return result

    def evaluate_all(
        self,
        fixtures: tuple[BenchmarkResumeFixture, ...] | None = None,
        *,
        check_drift: bool = True,
    ) -> BenchmarkRunResult:
        items = fixtures or ALL_BENCHMARK_FIXTURES
        results = [
            self.evaluate_fixture(f, check_drift=check_drift) for f in items
        ]
        contamination = [
            c for r in results for c in r.contamination if c.is_contaminated
        ]
        drift = [d for r in results for d in r.drift_warnings]
        return BenchmarkRunResult(
            results=results,
            contamination=contamination,
            drift_warnings=drift,
        )
