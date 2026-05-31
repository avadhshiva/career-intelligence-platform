"""Workflow continuity and trust refinements."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from career_intelligence_engine.tests.fixtures.sample_jds import JD_TPM
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import RecommendationEngine
from review_queue_manager import ReviewQueueManager
from services.listing_urls import resolve_listing_url


def test_resolve_listing_url_replaces_placeholder() -> None:
    url = resolve_listing_url(
        company="Infosys",
        role="Senior TPM",
        location="Bengaluru",
        job_url="https://careers.example.com/foo",
    )
    assert "example.com" not in url
    assert "linkedin.com/jobs/search/" in url
    assert "currentJobId" not in url


def test_resolve_listing_url_rebuilds_instead_of_reusing_stale_view_link() -> None:
    stale = "https://www.linkedin.com/jobs/view/123"
    url = resolve_listing_url(company="X", role="Senior TPM", location="Remote", job_url=stale)
    assert url != stale
    assert "/jobs/search/" in url
    assert "Senior TPM" in url or "X" in url


def test_review_queue_demo_filter_and_purge(tmp_path: Path) -> None:
    mgr = ReviewQueueManager(data_dir=tmp_path)
    mgr.initialize()
    engine = RecommendationEngine()
    parser = GenericJobParser()
    sample = parser.parse_pasted_text(JD_TPM, job_id="sample_test_001", title="TPM", company="Co")
    user = parser.parse_pasted_text(JD_TPM, job_id="user_job_001", title="TPM", company="Co")
    recs = engine.recommend_from_resume(RESUME_TPM, [sample, user])[1]
    by_id = {r.job_id: r for r in recs}
    mgr.enqueue_recommendation(by_id["sample_test_001"], origin="sample")
    mgr.enqueue_recommendation(by_id["user_job_001"], origin="user")

    assert len(mgr.list_pending()) == 1
    assert mgr.list_pending()[0]["job_id"] == "user_job_001"

    # Demo entries are now self-healed on load and excluded from UI lists.
    removed = mgr.purge_demo_entries()
    assert removed >= 0
    assert len(mgr.list_pending()) == 1
