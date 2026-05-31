"""Phase 5D application tracker tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from application_tracking.models import ApplicationStatus
from application_tracking.tracker import ApplicationTracker
from application_tracking.analytics import ApplicationAnalytics
from application_workspace.models import ApplicationApprovalState
from application_workspace.package_builder import ApplicationPackageBuilder
from application_workspace.review_manager import ApplicationReviewManager
from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from career_intelligence_engine.tests.fixtures.sample_jds import JD_TPM, JD_PRODUCT
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import RecommendationEngine


@pytest.fixture
def tmp_tracker(tmp_path: Path) -> ApplicationTracker:
    t = ApplicationTracker(data_dir=tmp_path / "tracking")
    t.initialize()
    return t


@pytest.fixture
def tmp_review(tmp_path: Path) -> ApplicationReviewManager:
    m = ApplicationReviewManager(data_dir=tmp_path / "packages")
    m.initialize()
    return m


def test_tracker_sync_on_package_save(
    tmp_tracker: ApplicationTracker,
    tmp_path: Path,
) -> None:
    tmp_review = ApplicationReviewManager(
        data_dir=tmp_path / "packages",
        tracker=tmp_tracker,
    )
    tmp_review.initialize()
    engine = RecommendationEngine()
    parser = GenericJobParser()
    posting = parser.parse_pasted_text(JD_TPM, job_id="tr1", title="TPM", company="Acme")
    rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
    builder = ApplicationPackageBuilder(tmp_review)
    pkg = builder.build(rec, RESUME_TPM, persist=True)
    tmp_review.approve(pkg.package_id)
    rec_saved = tmp_tracker.get_by_package(pkg.package_id)
    assert rec_saved is not None
    assert rec_saved.status == ApplicationStatus.APPROVED
    assert rec_saved.company == "Acme"
    assert rec_saved.resume_version == pkg.tailored_resume_id


def test_tracker_status_update_persistence(tmp_tracker: ApplicationTracker) -> None:
    from application_tracking.models import ApplicationRecord, utc_now_iso
    import uuid

    rec = ApplicationRecord(
        application_id=str(uuid.uuid4()),
        package_id="pkg-1",
        job_id="j1",
        company="Co",
        role="TPM",
        status=ApplicationStatus.EXPORTED,
        created_at=utc_now_iso(),
    )
    tmp_tracker.upsert(rec)
    updated = tmp_tracker.update_status(rec.application_id, ApplicationStatus.APPLIED, notes="submitted")
    assert updated.status == ApplicationStatus.APPLIED
    assert updated.applied_at
    reloaded = tmp_tracker.get(rec.application_id)
    assert reloaded.status == ApplicationStatus.APPLIED
    store = json.loads((tmp_tracker._store_path).read_text(encoding="utf-8"))
    assert len(store["applications"]) == 1


def test_dashboard_aggregation(
    tmp_tracker: ApplicationTracker,
    tmp_review: ApplicationReviewManager,
) -> None:
    engine = RecommendationEngine()
    parser = GenericJobParser()
    builder = ApplicationPackageBuilder(tmp_review)
    for job_id, jd in [("d1", JD_TPM), ("d2", JD_PRODUCT)]:
        title = "Technical Program Manager" if job_id == "d1" else "Product Manager"
        posting = parser.parse_pasted_text(jd, job_id=job_id, title=title, company="Co")
        rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
        pkg = builder.build(rec, RESUME_TPM, persist=True)
        if job_id == "d1":
            tmp_review.approve(pkg.package_id)
        else:
            tmp_review.reject(pkg.package_id, reason="misfit")

    metrics = ApplicationAnalytics(tmp_review, tmp_tracker).compute_dashboard()
    assert metrics.total_packages == 2
    assert metrics.rejection_rate > 0
    assert metrics.approval_rate > 0
    assert metrics.per_application
