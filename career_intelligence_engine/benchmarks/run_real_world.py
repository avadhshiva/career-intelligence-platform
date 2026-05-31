"""CLI: python -m career_intelligence_engine.benchmarks.run_real_world"""

from __future__ import annotations

import argparse
import sys

from career_intelligence_engine.benchmarks.real_world.evaluator import (
    RealWorldBenchmarkEvaluator,
)
from career_intelligence_engine.benchmarks.real_world.loader import load_all_fixtures
from career_intelligence_engine.benchmarks.regression import (
    build_snapshot,
    compare_against_baseline,
    save_snapshot,
)


def _print_summary(summary) -> None:
    print("\n=== REAL-WORLD BENCHMARK SUMMARY ===")
    print(f"fixtures:               {summary.fixture_count}")
    print(f"primary accuracy:       {summary.primary_accuracy:.1%}")
    print(f"adjacency precision:    {summary.adjacency_precision:.1%}")
    print(f"contamination rate:     {summary.contamination_rate:.1%}")
    print(f"exclusion correctness:  {summary.exclusion_correctness:.1%}")
    print(f"confidence calibration: {summary.confidence_calibration:.1%}")
    print(f"drift warnings:         {summary.drift_warning_count}")
    print(f"overall:                {'PASS' if summary.all_passed else 'FAIL'}")

    if summary.regressions:
        print("\n=== REGRESSION FAILURES ===")
        for msg in summary.regressions:
            print(f"  {msg}")

    print("\n=== FIXTURE RESULTS ===")
    for r in summary.fixture_results:
        status = "PASS" if r.passed else "FAIL"
        notes = "; ".join(r.failures) if r.failures else ""
        print(
            f"  {r.fixture_id:<36} {status:<6} "
            f"conf={r.confidence_score:.3f} {notes}"
        )

    drift_fixtures = [r for r in summary.fixture_results if r.drift_warnings]
    if drift_fixtures:
        print("\n=== BENCHMARK DRIFT WARNINGS ===")
        for r in drift_fixtures:
            for w in r.drift_warnings:
                print(f"  {w}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Real-world anonymized resume benchmark evaluation."
    )
    parser.add_argument(
        "--no-drift",
        action="store_true",
        help="Skip score drift comparison against baseline_scores.json.",
    )
    parser.add_argument(
        "--update-snapshots",
        action="store_true",
        help="Refresh regression snapshots from current engine output.",
    )
    parser.add_argument(
        "--check-regression",
        action="store_true",
        default=True,
        help="Compare against saved regression snapshots (default: on).",
    )
    parser.add_argument(
        "--no-regression",
        action="store_true",
        help="Skip regression snapshot comparison.",
    )
    args = parser.parse_args(argv)

    fixtures = load_all_fixtures()
    if not fixtures:
        print("No real-world fixtures found in benchmarks/real_world/fixtures/")
        return 1

    evaluator = RealWorldBenchmarkEvaluator()
    summary = evaluator.evaluate_all(fixtures, check_drift=not args.no_drift)

    if args.update_snapshots:
        for fixture in fixtures:
            profile = evaluator._engine.analyze_text(fixture.resume_text)
            snap = build_snapshot(fixture.fixture_id, profile)
            path = save_snapshot(snap)
            print(f"Updated snapshot: {path}")

    if not args.no_regression and args.check_regression:
        for fixture in fixtures:
            profile = evaluator._engine.analyze_text(fixture.resume_text)
            comparison = compare_against_baseline(fixture.fixture_id, profile)
            if comparison is not None and not comparison.passed:
                summary.regressions.extend(
                    f"{fixture.fixture_id}: {f}" for f in comparison.failures
                )
                for r in summary.fixture_results:
                    if r.fixture_id == fixture.fixture_id:
                        r.passed = False
                        r.failures.extend(comparison.failures)
        summary.all_passed = all(r.passed for r in summary.fixture_results)

    _print_summary(summary)
    return 0 if summary.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
