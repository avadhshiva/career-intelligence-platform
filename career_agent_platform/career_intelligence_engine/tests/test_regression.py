"""Tests for regression snapshot comparison."""

from __future__ import annotations

import tempfile
from pathlib import Path

from career_intelligence_engine.benchmarks.regression import (
    build_snapshot,
    compare_snapshots,
    load_snapshot,
    save_snapshot,
)
from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.tests.benchmark_resumes import BENCHMARK_FIXTURE_BY_ID


def test_snapshot_roundtrip() -> None:
    engine = CareerIdentityEngine()
    fixture = BENCHMARK_FIXTURE_BY_ID["ai_transformation_director"]
    profile = engine.analyze_text(fixture.resume_text)
    snap = build_snapshot(fixture.fixture_id, profile)

    with tempfile.TemporaryDirectory() as tmp:
        path = save_snapshot(snap, Path(tmp))
        loaded = load_snapshot(fixture.fixture_id, Path(tmp))
        assert loaded is not None
        assert loaded.primary == snap.primary
        assert path.exists()


def test_compare_identical_snapshots_passes() -> None:
    engine = CareerIdentityEngine()
    fixture = BENCHMARK_FIXTURE_BY_ID["technical_program_manager_enterprise"]
    profile = engine.analyze_text(fixture.resume_text)
    snap = build_snapshot(fixture.fixture_id, profile)
    comparison = compare_snapshots(snap, snap)
    assert comparison.passed
