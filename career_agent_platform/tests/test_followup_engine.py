"""Phase 5D follow-up reminder engine tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from application_tracking.followup_engine import FollowUpEngine, _business_days_between
from application_tracking.models import ApplicationRecord, ApplicationStatus, utc_now_iso
from application_tracking.tracker import ApplicationTracker


@pytest.fixture
def tmp_tracker(tmp_path: Path) -> ApplicationTracker:
    t = ApplicationTracker(data_dir=tmp_path / "tracking")
    t.initialize()
    return t


def test_business_days_between() -> None:
    mon = date(2026, 5, 18)
    next_mon = date(2026, 5, 25)
    assert _business_days_between(mon, next_mon) == 5


def test_stale_approved_reminder(tmp_tracker: ApplicationTracker) -> None:
    old = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    rec = ApplicationRecord(
        application_id="a1",
        package_id="p1",
        job_id="j1",
        company="Stale Co",
        role="TPM",
        status=ApplicationStatus.APPROVED,
        created_at=old,
        updated_at=old,
        last_action_at=old,
    )
    tmp_tracker.upsert(rec)
    report = FollowUpEngine(tmp_tracker).evaluate(today=datetime.now(timezone.utc).date())
    assert any("Stale Co" in f.company for f in report.pending_followups)
    assert any("Export" in f.recommended_action for f in report.pending_followups)


def test_applied_no_response_reminder(tmp_tracker: ApplicationTracker) -> None:
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    rec = ApplicationRecord(
        application_id="a2",
        package_id="p2",
        job_id="j2",
        company="Applied Co",
        role="Lead",
        status=ApplicationStatus.APPLIED,
        applied_at=old,
        last_action_at=old,
        created_at=old,
        updated_at=old,
    )
    tmp_tracker.upsert(rec)
    report = FollowUpEngine(tmp_tracker).evaluate()
    assert any(r.application_id == "a2" for r in report.pending_followups)


def test_interview_prep_reminder(tmp_tracker: ApplicationTracker) -> None:
    recent = datetime.now(timezone.utc).isoformat()
    rec = ApplicationRecord(
        application_id="a3",
        package_id="p3",
        job_id="j3",
        company="Interview Co",
        role="Director",
        status=ApplicationStatus.INTERVIEWING,
        last_action_at=recent,
        created_at=recent,
        updated_at=recent,
    )
    tmp_tracker.upsert(rec)
    report = FollowUpEngine(tmp_tracker).evaluate()
    assert any("interview prep" in f.recommended_action.lower() for f in report.pending_followups)


def test_deterministic_reminder_order(tmp_tracker: ApplicationTracker) -> None:
    for i in range(3):
        days_ago = (datetime.now(timezone.utc) - timedelta(days=5 + i)).isoformat()
        tmp_tracker.upsert(
            ApplicationRecord(
                application_id=f"id{i}",
                package_id=f"p{i}",
                job_id=f"j{i}",
                company=f"Co{i}",
                role="R",
                status=ApplicationStatus.APPLIED,
                last_action_at=days_ago,
                created_at=days_ago,
                updated_at=days_ago,
            ),
        )
    r1 = FollowUpEngine(tmp_tracker).evaluate()
    r2 = FollowUpEngine(tmp_tracker).evaluate()
    assert [f.application_id for f in r1.pending_followups] == [
        f.application_id for f in r2.pending_followups
    ]
