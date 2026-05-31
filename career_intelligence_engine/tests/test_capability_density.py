"""Calibration tests for capability density scoring."""

from __future__ import annotations

import pytest

from career_intelligence_engine.intelligence.capability_density import (
    score_capability_density,
    score_text_for_family,
)


STRONG_LEADERSHIP = """
• Led enterprise-wide AI transformation across global matrix organization
• Owned portfolio governance and steering committee facilitation
• Directed cross-BU program delivery with executive reporting
"""

WEAK_PARTICIPATION = """
• Participated in transformation initiative
• Assisted with program coordination
• Supported team delivery activities
"""


def test_leadership_verbs_increase_density() -> None:
    strong = score_capability_density(STRONG_LEADERSHIP, STRONG_LEADERSHIP.strip().split("\n"))
    weak = score_capability_density(WEAK_PARTICIPATION, WEAK_PARTICIPATION.strip().split("\n"))
    assert strong.total_density > weak.total_density
    assert strong.ownership_score > weak.ownership_score


def test_enterprise_scope_boosts_density() -> None:
    result = score_capability_density(
        STRONG_LEADERSHIP,
        [line.strip("• ").strip() for line in STRONG_LEADERSHIP.strip().split("\n") if line.strip()],
    )
    assert result.enterprise_scope_score > 0.3


def test_led_scores_higher_than_participated() -> None:
    led_bullets = ["Led enterprise transformation program"]
    part_bullets = ["Participated in transformation program"]
    led = score_capability_density("", led_bullets)
    part = score_capability_density("", part_bullets)
    assert led.ownership_score > part.ownership_score


def test_family_scoring_with_density() -> None:
    signals = ["program governance", "steering committee", "portfolio"]
    strong_score = score_text_for_family(
        STRONG_LEADERSHIP,
        [b.strip("• ").strip() for b in STRONG_LEADERSHIP.strip().split("\n") if b.strip()],
        signals,
    )
    weak_score = score_text_for_family(
        WEAK_PARTICIPATION,
        [b.strip("• ").strip() for b in WEAK_PARTICIPATION.strip().split("\n") if b.strip()],
        signals,
    )
    assert strong_score > weak_score


def test_human_readable_output() -> None:
    result = score_capability_density(
        STRONG_LEADERSHIP,
        [b.strip("• ").strip() for b in STRONG_LEADERSHIP.strip().split("\n") if b.strip()],
    )
    assert len(result.human_readable) >= 1
    assert all(len(h) > 20 for h in result.human_readable)


def test_density_bounded_zero_one() -> None:
    result = score_capability_density(STRONG_LEADERSHIP, [])
    assert 0.0 <= result.total_density <= 1.0
