"""Read-only recommendation governance metadata (no scoring impact)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from career_intelligence_engine.ontology.version import get_ontology_version
from evaluation.recommendation_snapshot import capture_snapshot
from monitoring.reliability_signals import benchmark_signature
from recommendation_engine import RecommendationResult
from version import BUILD_INFO


def _deterministic_mode_label() -> str:
    if BUILD_INFO.get("deterministic"):
        return "enabled (fixed inputs → stable ranking)"
    return "unknown"


def collect_governance_metadata(
    recommendations: list[RecommendationResult],
    *,
    resume_text: str = "",
    profile_primary_track: str = "",
) -> dict[str, Any]:
    snap = capture_snapshot(
        recommendations,
        resume_text=resume_text,
        profile_primary_track=profile_primary_track,
    )
    bench = "skipped"
    try:
        bench = benchmark_signature()
    except Exception:
        bench = "unavailable"
    return {
        "recommendation_hash": snap.recommendation_hash,
        "ontology_version": snap.ontology_version or get_ontology_version(),
        "benchmark_signature": bench,
        "deterministic_mode": _deterministic_mode_label(),
        "result_count": len(recommendations),
        "snapshot_id": snap.snapshot_id,
    }


def render_governance_panel(
    recommendations: list[RecommendationResult],
    *,
    resume_text: str = "",
    profile_primary_track: str = "",
) -> None:
    """Lightweight footer expander — no layout redesign."""
    if not recommendations:
        return
    meta = collect_governance_metadata(
        recommendations,
        resume_text=resume_text,
        profile_primary_track=profile_primary_track,
    )
    with st.expander("Recommendation governance", expanded=False):
        c1, c2 = st.columns(2)
        c1.markdown(f"**Recommendation hash** `{meta['recommendation_hash']}`")
        c2.markdown(f"**Ontology version** `{meta['ontology_version']}`")
        bench = meta["benchmark_signature"]
        bench_label = "available" if bench not in ("skipped", "unavailable") else bench
        st.caption(
            f"Benchmark signature: {bench_label} · "
            f"Deterministic mode: {meta['deterministic_mode']} · "
            f"Results: {meta['result_count']}"
        )
        if bench not in ("skipped", "unavailable"):
            st.code(bench, language=None)
        st.caption(f"Snapshot id: `{meta['snapshot_id']}`")
