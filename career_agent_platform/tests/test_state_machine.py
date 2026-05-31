"""Phase 5D state machine tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from application_workspace.models import ApplicationApprovalState
from application_workspace.review_manager import ApplicationReviewManager
from application_workspace.state_machine import can_transition, allowed_targets
from application_workspace.package_builder import ApplicationPackageBuilder
from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from career_intelligence_engine.tests.fixtures.sample_jds import JD_TPM
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import RecommendationEngine


@pytest.fixture
def tmp_review(tmp_path: Path) -> ApplicationReviewManager:
    mgr = ApplicationReviewManager(data_dir=tmp_path / "packages")
    mgr.initialize()
    return mgr


@pytest.fixture
def builder(tmp_review: ApplicationReviewManager) -> ApplicationPackageBuilder:
    return ApplicationPackageBuilder(tmp_review)


def _pkg(builder: ApplicationPackageBuilder, engine: RecommendationEngine, parser: GenericJobParser):
    posting = parser.parse_pasted_text(JD_TPM, job_id="sm1", title="TPM", company="Co")
    rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
    return builder.build(rec, RESUME_TPM, persist=True)


def test_allowed_transitions_map() -> None:
    assert ApplicationApprovalState.APPROVED in allowed_targets(
        ApplicationApprovalState.GENERATED,
    )
    assert ApplicationApprovalState.REOPENED in allowed_targets(
        ApplicationApprovalState.EXPORTED,
    )
    assert not can_transition(
        ApplicationApprovalState.EXPORTED,
        ApplicationApprovalState.APPROVED,
    )


def test_valid_transition_chain(
    tmp_review: ApplicationReviewManager,
    builder: ApplicationPackageBuilder,
) -> None:
    engine = RecommendationEngine()
    parser = GenericJobParser()
    pkg = _pkg(builder, engine, parser)
    r1 = tmp_review.mark_under_review(pkg.package_id)
    assert r1.success
    r2 = tmp_review.approve(pkg.package_id)
    assert r2.success
    r3 = tmp_review.mark_exported(pkg.package_id)
    assert r3.success
    reloaded = tmp_review.get_package(pkg.package_id)
    assert reloaded.approval_status == ApplicationApprovalState.EXPORTED
    assert len(reloaded.state_history) >= 4


def test_invalid_transition_does_not_crash(
    tmp_review: ApplicationReviewManager,
    builder: ApplicationPackageBuilder,
) -> None:
    engine = RecommendationEngine()
    parser = GenericJobParser()
    pkg = _pkg(builder, engine, parser)
    tmp_review.approve(pkg.package_id)
    tmp_review.mark_exported(pkg.package_id)
    bad = tmp_review.approve(pkg.package_id)
    assert not bad.success
    assert bad.warning
    reloaded = tmp_review.get_package(pkg.package_id)
    assert reloaded.approval_status == ApplicationApprovalState.EXPORTED
    blocked = [h for h in reloaded.state_history if not h.success]
    assert blocked
    assert blocked[-1].warning


def test_reopen_and_reapprove_flow(
    tmp_review: ApplicationReviewManager,
    builder: ApplicationPackageBuilder,
) -> None:
    engine = RecommendationEngine()
    parser = GenericJobParser()
    pkg = _pkg(builder, engine, parser)
    tmp_review.approve(pkg.package_id)
    tmp_review.mark_exported(pkg.package_id)
    r_reopen = tmp_review.reopen(pkg.package_id)
    assert r_reopen.success
    r_approve = tmp_review.approve(pkg.package_id)
    assert r_approve.success
    final = tmp_review.get_package(pkg.package_id)
    assert final.approval_status == ApplicationApprovalState.APPROVED


def test_rejected_to_archived(
    tmp_review: ApplicationReviewManager,
    builder: ApplicationPackageBuilder,
) -> None:
    engine = RecommendationEngine()
    parser = GenericJobParser()
    pkg = _pkg(builder, engine, parser)
    tmp_review.reject(pkg.package_id, reason="low priority")
    r = tmp_review.archive(pkg.package_id)
    assert r.success
    assert tmp_review.get_package(pkg.package_id).approval_status == ApplicationApprovalState.ARCHIVED


def test_state_history_persisted(
    tmp_review: ApplicationReviewManager,
    builder: ApplicationPackageBuilder,
) -> None:
    engine = RecommendationEngine()
    parser = GenericJobParser()
    pkg = _pkg(builder, engine, parser)
    tmp_review.approve(pkg.package_id, notes="good")
    path = tmp_review._package_path(pkg.package_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["state_history"]
    assert data["state_history"][-1]["success"] is True
    assert data["state_history"][-1]["review_notes"] == "good"
