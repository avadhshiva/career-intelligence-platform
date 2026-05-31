"""Tests for contamination diagnostics."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.contamination_analysis import (
    analyze_contamination,
)


@pytest.fixture
def engine() -> CareerIdentityEngine:
    return CareerIdentityEngine()


def test_contamination_signals_in_explanations(engine: CareerIdentityEngine) -> None:
    from career_intelligence_engine.tests.benchmark_resumes import BENCHMARK_FIXTURE_BY_ID

    fixture = BENCHMARK_FIXTURE_BY_ID["technical_program_manager_enterprise"]
    profile = engine.analyze_text(fixture.resume_text)
    signals = analyze_contamination(profile)
    assert isinstance(signals, list)
    assert "contamination_signals" in profile.explanations


def test_contamination_signal_structure(engine: CareerIdentityEngine) -> None:
    text = """
HR Business Partner | Corp | 2018 – Present
• Employee relations, talent acquisition, organizational development
• Culture transformation and people programs
"""
    profile = engine.analyze_text(text)
    for sig in analyze_contamination(profile):
        assert sig.family
        assert 0.0 <= sig.contamination_score <= 1.0
        assert isinstance(sig.reasons, list)
