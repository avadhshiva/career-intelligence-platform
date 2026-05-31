"""Evaluation infrastructure — snapshots, diffs, diagnostics (no scoring changes)."""

from __future__ import annotations

from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from career_intelligence_engine.tests.fixtures.sample_jds import JD_TPM
from evaluation.evaluation_report import build_evaluation_report, format_report_text
from evaluation.recommendation_diff import diff_snapshots
from evaluation.recommendation_diagnostics import build_recommendation_diagnostics
from evaluation.recommendation_snapshot import capture_snapshot, load_snapshot, write_snapshot
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import RecommendationEngine


def test_snapshot_identical_runs_same_hash() -> None:
    parser = GenericJobParser()
    posting = parser.parse_pasted_text(JD_TPM, job_id="eval_tpm", title="TPM", company="Co")
    engine = RecommendationEngine()
    _, recs1 = engine.recommend_from_resume(RESUME_TPM, [posting])
    _, recs2 = engine.recommend_from_resume(RESUME_TPM, [posting])
    s1 = capture_snapshot(recs1, resume_text=RESUME_TPM, label="a")
    s2 = capture_snapshot(recs2, resume_text=RESUME_TPM, label="b")
    assert s1.recommendation_hash == s2.recommendation_hash
    assert s1.items[0]["overall_match"] == s2.items[0]["overall_match"]


def test_diff_detects_score_change() -> None:
    baseline = {
        "items": [
            {
                "job_id": "j1",
                "overall_match": 0.5,
                "recommendation_priority": "GOOD_MATCH",
                "primary_role_family": "technical_program_management",
                "role_cluster": "tpm",
            },
        ],
    }
    current = {
        "items": [
            {
                "job_id": "j1",
                "overall_match": 0.6,
                "recommendation_priority": "STRONG_MATCH",
                "primary_role_family": "technical_program_management",
                "role_cluster": "tpm",
            },
        ],
    }
    diff = diff_snapshots(baseline, current)
    assert diff["has_changes"]
    assert len(diff["score_deltas"]) == 1
    assert len(diff["priority_changes"]) == 1


def test_evaluation_report_text() -> None:
    report = build_evaluation_report(
        {"items": [], "recommendation_hash": "a", "ontology_version": "v1"},
        {"items": [{"job_id": "x", "overall_match": 1.0, "recommendation_priority": "LOW_MATCH"}], "recommendation_hash": "b", "ontology_version": "v1"},
    )
    text = format_report_text(report)
    assert "Added roles: 1" in text


def test_diagnostics_attached_in_match_detail() -> None:
    parser = GenericJobParser()
    posting = parser.parse_pasted_text(JD_TPM, job_id="diag_tpm", title="TPM", company="Co")
    engine = RecommendationEngine()
    profile, recs = engine.recommend_from_resume(RESUME_TPM, [posting])
    assert recs
    diag = (recs[0].match_detail or {}).get("diagnostics") or {}
    assert diag.get("job_primary_family")
    assert "adjacency" in diag
    assert diag["adjacency"].get("reasoning")


def test_snapshot_roundtrip_tmp(tmp_path) -> None:
    parser = GenericJobParser()
    posting = parser.parse_pasted_text(JD_TPM, job_id="rt", title="TPM", company="Co")
    engine = RecommendationEngine()
    _, recs = engine.recommend_from_resume(RESUME_TPM, [posting])
    snap = capture_snapshot(recs, resume_text=RESUME_TPM)
    path = write_snapshot(tmp_path / "snap.json", snap)
    loaded = load_snapshot(path)
    assert loaded.recommendation_hash == snap.recommendation_hash


def test_build_diagnostics_direct() -> None:
    parser = GenericJobParser()
    posting = parser.parse_pasted_text(JD_TPM, job_id="direct", title="TPM", company="Co")
    engine = RecommendationEngine()
    profile = engine.analyze_resume(RESUME_TPM)
    job = posting.parsed_job_profile
    assert job is not None
    match = engine._matcher.match(profile, job)
    diag = build_recommendation_diagnostics(profile, job, match)
    assert diag["top_matching_dimensions"] is not None
