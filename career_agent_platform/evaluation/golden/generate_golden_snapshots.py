"""Regenerate committed golden recommendation snapshots (run after intentional ontology changes).

Usage (from career_agent_platform/):
  $env:PYTHONPATH = (Get-Location).Path
  python evaluation/golden/generate_golden_snapshots.py
"""

from __future__ import annotations

import json
from pathlib import Path

from career_intelligence_engine.tests.fixtures.calibration_resumes import (
    RESUME_ENGINEERING_MANAGER,
    RESUME_PROGRAM_DIRECTOR,
    RESUME_TPM,
)
from evaluation.golden import GOLDEN_DIR, GOLDEN_FIXTURE_IDS
from evaluation.recommendation_snapshot import capture_snapshot, write_snapshot
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import RecommendationEngine

_PLATFORM = Path(__file__).resolve().parents[2]
_JOB_FEED = _PLATFORM / "data" / "sample_job_feed.json"

_FIXTURES: dict[str, tuple[str, str]] = {
    "tpm_sample": (RESUME_TPM, "TPM calibration resume"),
    "delivery_leadership_sample": (RESUME_PROGRAM_DIRECTOR, "Delivery / program leadership"),
    "platform_engineering_sample": (RESUME_ENGINEERING_MANAGER, "Platform / engineering management"),
}


def _load_postings() -> list:
    parser = GenericJobParser()
    if not _JOB_FEED.exists():
        raise FileNotFoundError(f"Missing job feed: {_JOB_FEED}")
    return parser.parse_json_file(_JOB_FEED)


def generate_all() -> dict[str, str]:
    engine = RecommendationEngine()
    postings = _load_postings()
    hashes: dict[str, str] = {}
    for fixture_id in GOLDEN_FIXTURE_IDS:
        resume_text, label = _FIXTURES[fixture_id]
        profile, recs = engine.recommend_from_resume(resume_text, postings)
        track = getattr(profile.primary_career_track, "value", str(profile.primary_career_track))
        snap = capture_snapshot(
            recs,
            resume_text=resume_text,
            profile_primary_track=track,
            label=label,
            metadata={"fixture_id": fixture_id, "job_feed": str(_JOB_FEED.name)},
        )
        out = GOLDEN_DIR / f"{fixture_id}.json"
        write_snapshot(out, snap)
        hashes[fixture_id] = snap.recommendation_hash
    manifest = {
        "description": "Golden recommendation snapshots for deterministic regression",
        "job_feed": _JOB_FEED.name,
        "fixtures": list(GOLDEN_FIXTURE_IDS),
        "recommendation_hashes": hashes,
    }
    (GOLDEN_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return hashes


def main() -> None:
    hashes = generate_all()
    print(f"Wrote golden snapshots to {GOLDEN_DIR}")
    for fid, h in hashes.items():
        print(f"  {fid}: {h}")


if __name__ == "__main__":
    main()
