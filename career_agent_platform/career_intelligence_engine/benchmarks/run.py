"""CLI: python -m career_intelligence_engine.benchmarks.run"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from career_intelligence_engine.benchmarks.drift import (
    DRIFT_THRESHOLD_RATIO,
    load_baseline,
    save_baseline,
)
from career_intelligence_engine.benchmarks.evaluator import BenchmarkEvaluator
from career_intelligence_engine.benchmarks.metrics import BenchmarkMetricsSummary
from career_intelligence_engine.tests.benchmark_resumes import ALL_BENCHMARK_FIXTURES


def _print_pass_fail_table(summary: BenchmarkMetricsSummary) -> None:
    print("\n=== BENCHMARK PASS / FAIL ===")
    header = f"{'fixture':<40} {'primary':<8} {'status':<6} notes"
    print(header)
    print("-" * len(header))
    for r in summary.fixture_results:
        status = "PASS" if r.passed else "FAIL"
        primary_ok = "yes" if r.primary_correct else "no"
        notes = r.failure_summary() if not r.passed else ""
        print(f"{r.fixture_id:<40} {primary_ok:<8} {status:<6} {notes}")


def _print_ranking_diffs(summary: BenchmarkMetricsSummary) -> None:
    print("\n=== RANKING DIFFS (top 5 vs expected primary) ===")
    for r in summary.fixture_results:
        top5 = ", ".join(f"{fid.value}({score:.3f})" for fid, score in r.top_ranked[:5])
        marker = "OK" if r.primary_correct else "MISMATCH"
        print(f"[{marker}] {r.fixture_id}")
        print(f"  expected primary: {r.expected_primary.value}")
        print(f"  actual primary:   {r.actual_primary.value}")
        print(f"  top5: {top5}")
        if r.actual_adjacent:
            adj = ", ".join(a.value for a in r.actual_adjacent)
            print(f"  adjacent: {adj}")


def _print_calibration_regressions(summary: BenchmarkMetricsSummary) -> None:
    print("\n=== CALIBRATION REGRESSIONS (score drift > "
          f"{DRIFT_THRESHOLD_RATIO:.0%}) ===")
    if not summary.drift_warnings:
        print("No drift warnings (baseline missing or scores stable).")
        return
    for w in summary.drift_warnings:
        print(f"  REGRESSION: {w.message}")


def _print_contamination_causes(summary: BenchmarkMetricsSummary) -> None:
    print("\n=== ONTOLOGY CONTAMINATION WARNINGS ===")
    active = [c for c in summary.contamination_warnings if c.is_contaminated]
    if not active:
        print("No active contamination patterns detected.")
        return
    causes = Counter(c.cause for c in active)
    print("Top contamination causes:")
    for cause, count in causes.most_common():
        print(f"  [{count}x] {cause}")
    print("\nDetails:")
    for c in active:
        print(
            f"  {c.fixture_id}: {c.contaminant_family.value} "
            f"rank={c.contaminant_rank} ratio={c.score_ratio:.2f}"
        )


def _print_metrics(summary: BenchmarkMetricsSummary) -> None:
    print("\n=== BENCHMARK METRICS SUMMARY ===")
    m = summary.to_dict()
    print(f"fixtures:              {m['fixture_count']}")
    print(f"primary accuracy:      {m['primary_accuracy']:.1%}")
    print(f"adjacency accuracy:    {m['adjacency_accuracy']:.1%}")
    print(f"false-positive rate:   {m['false_positive_rate']:.1%}")
    print(f"contamination warnings:{m['contamination_warning_count']}")
    print(f"drift warnings:        {m['drift_warning_count']}")
    print(f"overall:               {'PASS' if m['all_passed'] else 'FAIL'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic benchmark evaluation for career intelligence engine."
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Refresh baseline_scores.json from current engine output.",
    )
    parser.add_argument(
        "--no-drift",
        action="store_true",
        help="Skip drift comparison against baseline.",
    )
    args = parser.parse_args(argv)

    evaluator = BenchmarkEvaluator()
    run = evaluator.evaluate_all(check_drift=not args.no_drift)
    summary = BenchmarkMetricsSummary.from_results(
        run.results,
        run.contamination,
        run.drift_warnings,
    )

    if args.update_baseline:
        snapshot: dict[str, dict[str, dict[str, float]]] = {}
        for fixture in ALL_BENCHMARK_FIXTURES:
            profile = evaluator._engine.analyze_text(fixture.resume_text)
            trace = profile.explanations.get("score_trace", [])
            snapshot[fixture.fixture_id] = {
                row["role_family"]: {
                    "ontology_score": float(row.get("ontology_score", 0)),
                    "final_score": float(row.get("final_score", 0)),
                }
                for row in trace
            }
        path = save_baseline(snapshot)
        print(f"Updated baseline: {path}")
        if not args.no_drift:
            run = evaluator.evaluate_all(check_drift=True)
            summary = BenchmarkMetricsSummary.from_results(
                run.results,
                run.contamination,
                run.drift_warnings,
            )

    _print_metrics(summary)
    _print_pass_fail_table(summary)
    _print_ranking_diffs(summary)
    _print_calibration_regressions(summary)
    _print_contamination_causes(summary)

    if not summary.all_passed:
        return 1
    if summary.drift_warnings and not args.update_baseline:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
