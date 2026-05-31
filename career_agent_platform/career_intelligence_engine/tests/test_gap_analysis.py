"""Tests for capability gap analysis."""

from __future__ import annotations

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.gap_analysis import analyze_capability_gaps
from career_intelligence_engine.models.ontology import RoleFamilyId


def test_gap_analysis_returns_missing_and_suggestions() -> None:
    vector = {
        "ai_strategy": 0.05,
        "transformation_strategy": 0.08,
        "executive_communication": 0.1,
        "delivery_execution": 0.4,
    }
    result = analyze_capability_gaps(vector, RoleFamilyId.AI_TRANSFORMATION)
    assert result.target_family == RoleFamilyId.AI_TRANSFORMATION.value
    assert result.target_display_name
    assert isinstance(result.missing_dimensions, list)
    assert isinstance(result.resume_strengthening, list)


def test_gap_analysis_in_profile_explanations() -> None:
    engine = CareerIdentityEngine()
    text = """
AI Transformation Director | Enterprise | 2019 – Present
• Enterprise AI strategy and operating model
• GenAI portfolio and organizational transformation
"""
    profile = engine.analyze_text(text)
    gap = profile.explanations.get("gap_analysis_primary")
    assert gap is not None
    assert gap.get("target_family") == profile.primary_career_track.value
