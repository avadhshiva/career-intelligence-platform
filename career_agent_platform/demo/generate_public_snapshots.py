"""Generate sanitized public demo artifacts (run once after engine changes).

Usage (from career_agent_platform/):
  $env:PYTHONPATH = (Get-Location).Path
  python demo/generate_public_snapshots.py
"""

from __future__ import annotations

import json
from pathlib import Path

from application_workspace.package_builder import ApplicationPackageBuilder
from career_intelligence_engine.tests.fixtures.sample_jds import JD_TPM
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import ApprovalStatus, RecommendationEngine

_PLATFORM = Path(__file__).resolve().parents[1]
_OUT = _PLATFORM / "demo" / "public"

# Fictional resume — no real people, companies, or contact details.
PUBLIC_SAMPLE_RESUME = """
Morgan Lee

EXPERIENCE
Senior Technical Program Manager | Example Industries | 2018 – Present
• Owned release train, SDLC alignment, and dependency management across engineering teams
• Coordinated architecture reviews and CI/CD adoption for enterprise cloud programs
• Led cross-functional technical delivery with executive stakeholder reporting
• Managed multi-region rollout for large enterprise transformation programs

Technical Program Manager | Sample Systems | 2013 – 2018
• Release governance, PI planning, and portfolio coordination

SKILLS
Program management, SDLC, agile, cloud platforms, governance, stakeholder management
""".strip()


def main() -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "sample_resume.txt").write_text(PUBLIC_SAMPLE_RESUME + "\n", encoding="utf-8")

    feed_src = _PLATFORM / "data" / "sample_job_feed.json"
    if feed_src.exists():
        (_OUT / "sample_job_feed.json").write_text(
            feed_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    engine = RecommendationEngine()
    parser = GenericJobParser()
    postings = parser.parse_json_file(_OUT / "sample_job_feed.json") if (_OUT / "sample_job_feed.json").exists() else []
    if not postings:
        postings = [
            parser.parse_pasted_text(
                JD_TPM,
                job_id="demo_public_tpm_001",
                title="Senior Technical Program Manager",
                company="Example Industries",
            ),
        ]

    profile, recs = engine.recommend_from_resume(PUBLIC_SAMPLE_RESUME, postings[:3])
    rec_dicts = [r.to_dict() for r in recs]
    (_OUT / "sample_recommendations.json").write_text(
        json.dumps(
            {
                "description": "Sanitized deterministic recommendations for public repo reviewers",
                "profile_primary_track": profile.primary_career_track.value,
                "recommendations": rec_dicts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    approved = recs[0] if recs else None
    if approved:
        approved.approval_status = ApprovalStatus.APPROVED
        builder = ApplicationPackageBuilder()
        pkg = builder.build(approved, PUBLIC_SAMPLE_RESUME, package_id="demo-public-pkg-001", persist=False)
        (_OUT / "sample_package.json").write_text(
            json.dumps(
                {
                    "description": "Sanitized application package snapshot (not persisted to applications/data)",
                    "package": pkg.to_dict() if hasattr(pkg, "to_dict") else {},
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    print(f"Wrote public demo artifacts to {_OUT}")


if __name__ == "__main__":
    main()
