"""Calibration tests for executive signal detection."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.executive_signals import detect_executive_signals
from career_intelligence_engine.models.ontology import ParsedResume

EXECUTIVE_RESUME = ParsedResume(
    raw_text="Senior Program Manager with enterprise governance experience",
    job_titles=["Senior Program Manager", "Program Director"],
    bullets=[
        "Led enterprise AI transformation with steering committee governance",
        "Chaired portfolio governance board with executive reporting cadence",
        "Owned AI strategy and organizational transformation across cross-BU teams",
        "Established enterprise PMO and transformation office operating model",
    ],
)

BASIC_RESUME = ParsedResume(
    raw_text="Software Engineer",
    job_titles=["Software Engineer"],
    bullets=[
        "Implemented microservices and unit tests",
        "Participated in code reviews",
    ],
)


def test_executive_governance_signals_detected() -> None:
    result = detect_executive_signals(EXECUTIVE_RESUME)
    assert result.enterprise_governance > 0.3
    assert result.executive_strength > 0.3
    assert "governance_board" in result.signals or "executive_cadence" in result.signals


def test_transformation_leadership_boost() -> None:
    result = detect_executive_signals(EXECUTIVE_RESUME)
    assert result.transformation_leadership > 0.3


def test_basic_resume_low_executive_scores() -> None:
    result = detect_executive_signals(BASIC_RESUME)
    assert result.executive_strength < 0.2
    assert result.transformation_leadership < 0.2


def test_human_readable_executive_signals() -> None:
    result = detect_executive_signals(EXECUTIVE_RESUME)
    assert len(result.human_readable) >= 2
    assert any("AI strategy" in h or "steering" in h.lower() or "governance" in h.lower()
               for h in result.human_readable)


def test_executive_governance_boosts_transformation_family_scoring() -> None:
    """Executive governance signals should produce high transformation leadership."""
    result = detect_executive_signals(EXECUTIVE_RESUME)
    assert result.transformation_leadership >= 0.35
    assert result.enterprise_governance >= 0.35


def test_scores_bounded() -> None:
    result = detect_executive_signals(EXECUTIVE_RESUME)
    assert 0.0 <= result.executive_strength <= 1.0
    assert 0.0 <= result.transformation_leadership <= 1.0
    assert 0.0 <= result.enterprise_governance <= 1.0
