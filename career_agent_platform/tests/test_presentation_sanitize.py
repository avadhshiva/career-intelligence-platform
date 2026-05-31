"""Tests for UI-only presentation sanitization."""

from __future__ import annotations

from presentation.sanitize import (
    format_score_percent,
    is_placeholder_text,
    resolve_snapshot_scores,
    sanitize_display_text,
    sanitize_gap_question,
)


def test_placeholder_detection() -> None:
    assert is_placeholder_text("unknown")
    assert is_placeholder_text("tmp_role_1")
    assert not is_placeholder_text("Senior TPM")


def test_sanitize_strips_internal_jargon() -> None:
    raw = "Score from deterministic_job_match_v1 outputs."
    cleaned = sanitize_display_text(raw)
    assert "deterministic_job_match_v1" not in cleaned.lower()


def test_format_score_percent_never_shows_zero_when_missing() -> None:
    assert format_score_percent(None) == "—"
    assert format_score_percent(0.0) == "—"
    assert format_score_percent(0.72) == "72%"


def test_resolve_snapshot_scores_fallback() -> None:
    fit, conf = resolve_snapshot_scores(
        {"overall_match": 0.0},
        package_confidence=0.81,
        resume_alignment=0.68,
    )
    assert fit == "68%"
    assert conf == "81%"


def test_sanitize_gap_question_filters_empty_topics() -> None:
    assert sanitize_gap_question("How would you address: unknown?") == ""


def test_sanitize_artifact_prose_replaces_tmp_titles() -> None:
    from presentation.sanitize import sanitize_artifact_prose

    raw = "Exploring the Tmp5Roiq3Fw opportunity at Unknown."
    cleaned = sanitize_artifact_prose(raw, job_title="Tmp5Roiq3Fw", company="Unknown")
    assert "Tmp5" not in cleaned
    assert "Unknown" not in cleaned
