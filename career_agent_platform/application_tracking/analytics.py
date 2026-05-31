"""Deterministic analytics and explainability aggregation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from application_tracking.models import ApplicationRecord, ApplicationStatus
from application_tracking.tracker import ApplicationTracker
from application_workspace.models import ApplicationApprovalState, ApplicationPackage
from application_workspace.review_manager import ApplicationReviewManager
from application_tracking.display_quality import (
    filter_aging_buckets,
    filter_company_scores,
    filter_role_families,
    is_low_quality_label,
)
from review_queue_manager import ReviewQueueManager
from state_hygiene import get_valid_packages, get_valid_tracker_records_for_packages


def _parse_ts(iso: str) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def _aging_bucket(iso: str, now: datetime) -> str:
    ts = _parse_ts(iso)
    if not ts:
        return "unknown"
    days = (now - ts).days
    if days <= 7:
        return "0-7 days"
    if days <= 14:
        return "8-14 days"
    if days <= 30:
        return "15-30 days"
    return "31+ days"


@dataclass
class ApplicationExplainability:
    package_id: str
    job_id: str
    company: str
    role: str
    why_approved: list[str] = field(default_factory=list)
    why_rejected: list[str] = field(default_factory=list)
    strongest_dimensions: list[str] = field(default_factory=list)
    recurring_gaps: list[str] = field(default_factory=list)
    recurring_risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "job_id": self.job_id,
            "company": self.company,
            "role": self.role,
            "why_approved": list(self.why_approved),
            "why_rejected": list(self.why_rejected),
            "strongest_dimensions": list(self.strongest_dimensions),
            "recurring_gaps": list(self.recurring_gaps),
            "recurring_risks": list(self.recurring_risks),
        }


@dataclass
class DashboardMetrics:
    total_applications: int = 0
    total_packages: int = 0
    approval_rate: float = 0.0
    export_rate: float = 0.0
    interview_rate: float = 0.0
    rejection_rate: float = 0.0
    top_role_families: list[tuple[str, int]] = field(default_factory=list)
    strongest_matching_companies: list[tuple[str, float]] = field(default_factory=list)
    aging_buckets: dict[str, int] = field(default_factory=dict)
    recurring_weaknesses: list[str] = field(default_factory=list)
    per_application: list[ApplicationExplainability] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_applications": self.total_applications,
            "total_packages": self.total_packages,
            "approval_rate": self.approval_rate,
            "export_rate": self.export_rate,
            "interview_rate": self.interview_rate,
            "rejection_rate": self.rejection_rate,
            "top_role_families": self.top_role_families,
            "strongest_matching_companies": self.strongest_matching_companies,
            "aging_buckets": self.aging_buckets,
            "recurring_weaknesses": self.recurring_weaknesses,
            "per_application": [p.to_dict() for p in self.per_application],
        }


class ApplicationAnalytics:
    """Aggregate deterministic metrics from packages, tracker, and review queue."""

    def __init__(
        self,
        review_manager: ApplicationReviewManager | None = None,
        tracker: ApplicationTracker | None = None,
        queue_manager: ReviewQueueManager | None = None,
    ) -> None:
        self._review = review_manager or ApplicationReviewManager()
        self._tracker = tracker or ApplicationTracker()
        self._queue = queue_manager or ReviewQueueManager()

    def _load_packages(self) -> list[ApplicationPackage]:
        return get_valid_packages(self._review)

    def explain_package(self, pkg: ApplicationPackage) -> ApplicationExplainability:
        snap = pkg.recommendation_snapshot or {}
        approved = pkg.approval_status in (
            ApplicationApprovalState.APPROVED,
            ApplicationApprovalState.EXPORTED,
            ApplicationApprovalState.REOPENED,
        )
        return ApplicationExplainability(
            package_id=pkg.package_id,
            job_id=pkg.source_job_id,
            company=pkg.company,
            role=pkg.job_title,
            why_approved=list(snap.get("why_matched") or []) if approved else [],
            why_rejected=list(snap.get("why_not_matched") or [])
            + ([pkg.rejection_reason] if pkg.rejection_reason else []),
            strongest_dimensions=list(snap.get("dominant_dimensions") or []),
            recurring_gaps=list(snap.get("gaps") or snap.get("missing_capabilities") or []),
            recurring_risks=list(snap.get("risks") or snap.get("top_risks") or []),
        )

    def compute_dashboard(self) -> DashboardMetrics:
        now = datetime.now(timezone.utc)
        packages = self._load_packages()
        valid_pkg_ids = {p.package_id for p in packages}
        apps = get_valid_tracker_records_for_packages(self._tracker, valid_package_ids=valid_pkg_ids)

        pkg_approved = sum(
            1
            for p in packages
            if p.approval_status
            in (
                ApplicationApprovalState.APPROVED,
                ApplicationApprovalState.EXPORTED,
                ApplicationApprovalState.REOPENED,
            )
        )
        pkg_exported = sum(
            1 for p in packages if p.approval_status == ApplicationApprovalState.EXPORTED
        )
        pkg_rejected = sum(
            1 for p in packages if p.approval_status == ApplicationApprovalState.REJECTED
        )
        total_pkg = len(packages) or 1

        interviewing = sum(1 for a in apps if a.status == ApplicationStatus.INTERVIEWING)

        role_counter: Counter[str] = Counter()
        company_scores: dict[str, list[float]] = {}
        gap_counter: Counter[str] = Counter()
        rejected_gap_counter: Counter[str] = Counter()
        aging: Counter[str] = Counter()

        per_app: list[ApplicationExplainability] = []
        for pkg in packages:
            per_app.append(self.explain_package(pkg))
            snap = pkg.recommendation_snapshot or {}
            rf = snap.get("match_detail", {}).get("primary_role_family") or snap.get(
                "primary_role_family",
                "unknown",
            )
            role_counter[str(rf)] += 1
            score = float(snap.get("overall_match", pkg.confidence))
            company_scores.setdefault(pkg.company, []).append(score)
            for g in snap.get("missing_dimensions") or snap.get("gaps") or []:
                gap_counter[str(g)] += 1
                if pkg.approval_status == ApplicationApprovalState.REJECTED:
                    rejected_gap_counter[str(g)] += 1
            aging[_aging_bucket(pkg.generated_at, now)] += 1

        top_companies = sorted(
            (
                (c, sum(v) / len(v))
                for c, v in company_scores.items()
                if not is_low_quality_label(c)
            ),
            key=lambda x: -x[1],
        )[:8]

        recurring: list[str] = []
        total_rej = sum(1 for p in packages if p.approval_status == ApplicationApprovalState.REJECTED)
        for gap, count in rejected_gap_counter.most_common(5):
            if total_rej:
                pct = int(100 * count / total_rej)
                recurring.append(f"{gap} appears in {pct}% of rejected packages.")
            elif gap_counter[gap]:
                pct = int(100 * gap_counter[gap] / max(len(packages), 1))
                recurring.append(f"{gap} appears in {pct}% of tracked packages.")

        return DashboardMetrics(
            total_applications=len(apps),
            total_packages=len(packages),
            approval_rate=pkg_approved / total_pkg,
            export_rate=pkg_exported / total_pkg,
            interview_rate=interviewing / max(len(apps), 1),
            rejection_rate=pkg_rejected / total_pkg,
            top_role_families=filter_role_families(role_counter.most_common(6)),
            strongest_matching_companies=filter_company_scores(top_companies),
            aging_buckets=filter_aging_buckets(dict(aging)),
            recurring_weaknesses=recurring,
            per_application=per_app,
        )
