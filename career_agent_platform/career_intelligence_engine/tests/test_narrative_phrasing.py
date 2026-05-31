"""Narrative phrasing — recruiter-grade copy without mechanical scoring language."""

from __future__ import annotations

import re

from career_intelligence_engine.narrative_phrasing import (
    compose_positioning_summary,
    phrase_gap,
    phrase_strength,
)


def test_strength_phrasing_avoids_job_weight() -> None:
    line = phrase_strength("enterprise_governance", 0.15)
    assert "job weight" not in line.lower()
    assert "%" not in line or "governance" in line.lower()


def test_gap_phrasing_strategic_for_transformation() -> None:
    line = phrase_gap("transformation_strategy", 0.1, 0.4)
    assert "less emphasized" in line.lower() or "transformation" in line.lower()
    assert "job requires" not in line.lower()


def test_positioning_summary_gate_failure() -> None:
    summary = compose_positioning_summary(
        job_display="Product Management",
        score=0.26,
        gate_passed=False,
        gate_reason="Product ownership evidence missing.",
        dominant_dims=[],
        weak_dims=[],
        strategic_pattern="",
    )
    assert "shortlist" in summary.lower()
    assert "26%" not in summary


def test_positioning_summary_strong_tier_no_percent_spam() -> None:
    summary = compose_positioning_summary(
        job_display="Technical Program Management",
        score=0.82,
        gate_passed=True,
        gate_reason="",
        dominant_dims=["technical_execution", "release_governance"],
        weak_dims=["change_management"],
        strategic_pattern="Profile is strongest in technical execution.",
    )
    assert "82%" not in summary
    assert "strong shortlist" in summary.lower()
