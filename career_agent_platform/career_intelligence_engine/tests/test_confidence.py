"""Tests for deterministic confidence scoring."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.confidence import compute_confidence
from career_intelligence_engine.models.evaluation import ConfidenceLevel


@pytest.fixture
def engine() -> CareerIdentityEngine:
    return CareerIdentityEngine()


def test_confidence_attached_to_profile(engine: CareerIdentityEngine) -> None:
    text = """
Senior Technical Program Manager | Global Corp | 2018 – Present
• Dependency management, release train, SDLC, architecture alignment
• Cross-functional engineering delivery
"""
    profile = engine.analyze_text(text)
    assert profile.confidence_result is not None
    assert profile.confidence_result.confidence_level in {
        l.value for l in ConfidenceLevel
    }
    assert 0.0 <= profile.confidence_result.confidence_score <= 1.0
    assert "confidence" in profile.explanations


def test_confidence_levels_are_deterministic(engine: CareerIdentityEngine) -> None:
    text = "AI Transformation Director — enterprise AI strategy and operating model"
    p1 = engine.analyze_text(text)
    p2 = engine.analyze_text(text)
    assert p1.confidence_result == p2.confidence_result


def test_compute_confidence_without_unified_returns_low() -> None:
    from career_intelligence_engine.models.candidate_profile import CandidateProfile

    profile = CandidateProfile()
    result = compute_confidence(profile)
    assert result.confidence_level == ConfidenceLevel.LOW.value
