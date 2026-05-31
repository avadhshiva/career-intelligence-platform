"""Optional reliability signals for deterministic recommendation runs."""

from __future__ import annotations

import os
from typing import Any

from career_intelligence_engine.benchmarks.evaluator import BenchmarkEvaluator
from career_intelligence_engine.benchmarks.metrics import BenchmarkMetricsSummary
from career_intelligence_engine.ontology.version import get_ontology_version
from evaluation.recommendation_snapshot import capture_snapshot, recommendation_hash
from monitoring.ops_log import log_event
from recommendation_engine import RecommendationResult


def benchmark_signature() -> str:
    """Lightweight fingerprint of benchmark fixture coverage (informational)."""
    flag = os.environ.get("CAREER_AGENT_BENCHMARK_SIGNALS", "").strip().lower()
    if flag not in ("1", "true", "yes"):
        return "skipped"
    evaluator = BenchmarkEvaluator()
    run = evaluator.evaluate_all(check_drift=False)
    summary = BenchmarkMetricsSummary.from_results(
        run.results,
        run.contamination,
        run.drift_warnings,
    )
    return (
        f"fixtures={summary.fixture_count}"
        f"|adjacency_hits={summary.adjacency_hits}/{summary.adjacency_expected}"
        f"|all_passed={summary.all_passed}"
    )


def log_recommendation_run_signals(
    recommendations: list[RecommendationResult],
    *,
    resume_text: str = "",
    profile_primary_track: str = "",
    posting_count: int = 0,
    extra: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Emit deterministic reliability fields to ops log (no scoring impact)."""
    snapshot = capture_snapshot(
        recommendations,
        resume_text=resume_text,
        profile_primary_track=profile_primary_track,
    )
    items = snapshot.items
    rec_hash = recommendation_hash(items) if items else snapshot.recommendation_hash
    ontology = get_ontology_version()
    try:
        bench_sig = benchmark_signature()
    except Exception:
        bench_sig = "unavailable"

    fields = {
        "recommendation_hash": rec_hash,
        "ontology_version": ontology,
        "benchmark_signature": bench_sig,
        "profile_primary_track": profile_primary_track,
        "posting_count": posting_count,
        "result_count": len(recommendations),
        **(extra or {}),
    }
    log_event("recommendation_reliability_signals", **fields)
    return {
        "recommendation_hash": rec_hash,
        "ontology_version": ontology,
        "benchmark_signature": bench_sig,
    }
