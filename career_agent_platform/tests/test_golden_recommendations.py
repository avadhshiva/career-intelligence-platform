"""Golden snapshot regression — deterministic recommendation_hash governance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from career_intelligence_engine.tests.fixtures.calibration_resumes import (
    RESUME_ENGINEERING_MANAGER,
    RESUME_PROGRAM_DIRECTOR,
    RESUME_TPM,
)
from evaluation.evaluation_report import build_evaluation_report, format_report_text
from evaluation.golden import GOLDEN_DIR, GOLDEN_FIXTURE_IDS
from evaluation.recommendation_snapshot import capture_snapshot, load_snapshot
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import RecommendationEngine

_PLATFORM = Path(__file__).resolve().parents[1]
_JOB_FEED = _PLATFORM / "data" / "sample_job_feed.json"

_RESUME_BY_FIXTURE: dict[str, str] = {
    "tpm_sample": RESUME_TPM,
    "delivery_leadership_sample": RESUME_PROGRAM_DIRECTOR,
    "platform_engineering_sample": RESUME_ENGINEERING_MANAGER,
}


def _run_fixture(fixture_id: str):
    resume_text = _RESUME_BY_FIXTURE[fixture_id]
    postings = GenericJobParser().parse_json_file(_JOB_FEED)
    engine = RecommendationEngine()
    profile, recs = engine.recommend_from_resume(resume_text, postings)
    track = getattr(profile.primary_career_track, "value", str(profile.primary_career_track))
    return capture_snapshot(
        recs,
        resume_text=resume_text,
        profile_primary_track=track,
        label=fixture_id,
        metadata={"fixture_id": fixture_id},
    )


@pytest.mark.parametrize("fixture_id", GOLDEN_FIXTURE_IDS)
def test_golden_recommendation_hash_matches_committed(fixture_id: str) -> None:
    golden_path = GOLDEN_DIR / f"{fixture_id}.json"
    assert golden_path.exists(), f"Missing golden snapshot: {golden_path}"
    golden = load_snapshot(golden_path)
    current = _run_fixture(fixture_id)

    if current.recommendation_hash == golden.recommendation_hash:
        return

    report = build_evaluation_report(golden.to_dict(), current.to_dict())
    diff = report.get("diff") or {}
    # Ontology-only drift without ranking changes should not reach here (hash would match).
    pytest.fail(
        "Golden recommendation drift detected for "
        f"{fixture_id}.\n"
        f"baseline hash={golden.recommendation_hash} current hash={current.recommendation_hash}\n"
        f"{format_report_text(report)}\n"
        f"diff summary: added={len(diff.get('added_roles') or [])} "
        f"removed={len(diff.get('removed_roles') or [])} "
        f"score_deltas={len(diff.get('score_deltas') or [])}",
    )


def test_golden_manifest_lists_all_fixtures() -> None:
    manifest_path = GOLDEN_DIR / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest.get("fixtures") == list(GOLDEN_FIXTURE_IDS)
    hashes = manifest.get("recommendation_hashes") or {}
    for fixture_id in GOLDEN_FIXTURE_IDS:
        assert fixture_id in hashes


def test_golden_generation_is_deterministic() -> None:
    a = _run_fixture("tpm_sample")
    b = _run_fixture("tpm_sample")
    assert a.recommendation_hash == b.recommendation_hash
