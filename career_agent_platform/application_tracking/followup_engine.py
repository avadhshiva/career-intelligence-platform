"""Deterministic follow-up reminder engine (no AI)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from application_tracking.models import ApplicationRecord, ApplicationStatus
from application_tracking.tracker import ApplicationTracker


@dataclass
class FollowUpReminder:
    application_id: str
    package_id: str
    company: str
    role: str
    days_since_last_action: int
    recommended_action: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "package_id": self.package_id,
            "company": self.company,
            "role": self.role,
            "days_since_last_action": self.days_since_last_action,
            "recommended_action": self.recommended_action,
            "reason": self.reason,
        }


@dataclass
class FollowUpReport:
    pending_followups: list[FollowUpReminder] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pending_followups": [f.to_dict() for f in self.pending_followups],
            "generated_at": self.generated_at,
        }


def _parse_date(iso: str) -> date | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _business_days_between(start: date, end: date) -> int:
    if start > end:
        return 0
    count = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            count += 1
    return count


def _days_since(iso: str, today: date | None = None) -> int:
    parsed = _parse_date(iso)
    if not parsed:
        return 0
    ref = today or datetime.now(timezone.utc).date()
    return (ref - parsed).days


class FollowUpEngine:
    """Rule-based reminders for human follow-up."""

    STALE_APPROVED_BUSINESS_DAYS = 7
    APPLIED_NO_RESPONSE_BUSINESS_DAYS = 5
    INTERVIEW_PREP_DAYS = 2

    def __init__(self, tracker: ApplicationTracker | None = None) -> None:
        self._tracker = tracker or ApplicationTracker()

    def evaluate(self, today: date | None = None) -> FollowUpReport:
        ref = today or datetime.now(timezone.utc).date()
        reminders: list[FollowUpReminder] = []

        for rec in self._tracker.list_all():
            last = _parse_date(rec.last_action_at) or _parse_date(rec.updated_at)
            days = _days_since(rec.last_action_at or rec.updated_at, ref)

            if rec.status == ApplicationStatus.APPLIED:
                biz = _business_days_between(last, ref) if last else days
                if biz >= self.APPLIED_NO_RESPONSE_BUSINESS_DAYS:
                    reminders.append(
                        FollowUpReminder(
                            application_id=rec.application_id,
                            package_id=rec.package_id,
                            company=rec.company,
                            role=rec.role,
                            days_since_last_action=days,
                            recommended_action="Follow up with recruiter or hiring manager",
                            reason=(
                                f"No recorded response {biz} business days after apply "
                                f"(threshold: {self.APPLIED_NO_RESPONSE_BUSINESS_DAYS})."
                            ),
                        ),
                    )

            if rec.status == ApplicationStatus.APPROVED:
                biz = _business_days_between(last, ref) if last else days
                if biz >= self.STALE_APPROVED_BUSINESS_DAYS:
                    reminders.append(
                        FollowUpReminder(
                            application_id=rec.application_id,
                            package_id=rec.package_id,
                            company=rec.company,
                            role=rec.role,
                            days_since_last_action=days,
                            recommended_action="Export and submit application",
                            reason=(
                                f"Package approved {biz} business days ago without export "
                                f"(threshold: {self.STALE_APPROVED_BUSINESS_DAYS})."
                            ),
                        ),
                    )

            if rec.status == ApplicationStatus.RECRUITER_CONTACTED:
                reminders.append(
                    FollowUpReminder(
                        application_id=rec.application_id,
                        package_id=rec.package_id,
                        company=rec.company,
                        role=rec.role,
                        days_since_last_action=days,
                        recommended_action="Log recruiter reply and schedule next step",
                        reason="Recruiter contact recorded; confirm reply and next action.",
                    ),
                )

            if rec.status == ApplicationStatus.INTERVIEWING:
                if days <= self.INTERVIEW_PREP_DAYS:
                    reminders.append(
                        FollowUpReminder(
                            application_id=rec.application_id,
                            package_id=rec.package_id,
                            company=rec.company,
                            role=rec.role,
                            days_since_last_action=days,
                            recommended_action="Review interview prep and gap narratives",
                            reason=(
                                f"Interview stage active; prep within "
                                f"{self.INTERVIEW_PREP_DAYS} days of last update."
                            ),
                        ),
                    )

            if rec.status == ApplicationStatus.EXPORTED and days >= 3:
                reminders.append(
                    FollowUpReminder(
                        application_id=rec.application_id,
                        package_id=rec.package_id,
                        company=rec.company,
                        role=rec.role,
                        days_since_last_action=days,
                        recommended_action="Mark as applied once submission is complete",
                        reason="Exported package not yet marked applied.",
                    ),
                )

        reminders.sort(key=lambda r: -r.days_since_last_action)
        return FollowUpReport(
            pending_followups=reminders,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
