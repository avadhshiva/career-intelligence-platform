"""JSON-backed application lifecycle tracker."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from application_tracking.models import (
    ApplicationRecord,
    ApplicationStatus,
    CompanyPipelineState,
    utc_now_iso,
)
from application_workspace.models import ApplicationApprovalState, ApplicationPackage


def _platform_root() -> Path:
    return Path(__file__).resolve().parents[1]


_PACKAGE_TO_STATUS: dict[ApplicationApprovalState, ApplicationStatus] = {
    ApplicationApprovalState.GENERATED: ApplicationStatus.SAVED,
    ApplicationApprovalState.UNDER_REVIEW: ApplicationStatus.SAVED,
    ApplicationApprovalState.APPROVED: ApplicationStatus.APPROVED,
    ApplicationApprovalState.EXPORTED: ApplicationStatus.EXPORTED,
    ApplicationApprovalState.REOPENED: ApplicationStatus.APPROVED,
    ApplicationApprovalState.REJECTED: ApplicationStatus.REJECTED,
    ApplicationApprovalState.ARCHIVED: ApplicationStatus.WITHDRAWN,
}


class ApplicationTracker:
    """Deterministic persistence for post-package application lifecycle."""

    def __init__(self, data_dir: Path | None = None) -> None:
        root = data_dir or (_platform_root() / "applications" / "data" / "application_tracking")
        self._root = root
        self._store_path = root / "applications.json"

    def initialize(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        if not self._store_path.exists():
            self._store_path.write_text(
                json.dumps({"applications": []}, indent=2),
                encoding="utf-8",
            )

    def _load(self) -> dict[str, Any]:
        self.initialize()
        return json.loads(self._store_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self._store_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_all(self) -> list[ApplicationRecord]:
        store = self._load()
        return [ApplicationRecord.from_dict(a) for a in store.get("applications") or []]

    def get_by_package(self, package_id: str) -> ApplicationRecord | None:
        for rec in self.list_all():
            if rec.package_id == package_id:
                return rec
        return None

    def get(self, application_id: str) -> ApplicationRecord:
        for rec in self.list_all():
            if rec.application_id == application_id:
                return rec
        raise KeyError(f"application_id not found: {application_id}")

    def upsert(self, record: ApplicationRecord) -> ApplicationRecord:
        store = self._load()
        apps = store.get("applications") or []
        now = utc_now_iso()
        record.updated_at = now
        if not record.last_action_at:
            record.last_action_at = now
        replaced = False
        for i, row in enumerate(apps):
            if row.get("application_id") == record.application_id:
                apps[i] = record.to_dict()
                replaced = True
                break
        if not replaced:
            if not record.created_at:
                record.created_at = now
            apps.append(record.to_dict())
        store["applications"] = sorted(apps, key=lambda x: x.get("updated_at", ""), reverse=True)
        self._save(store)
        return record

    def sync_from_package(self, package: ApplicationPackage) -> ApplicationRecord:
        """Mirror package approval state into tracker."""
        existing = self.get_by_package(package.package_id)
        status = _PACKAGE_TO_STATUS.get(package.approval_status, ApplicationStatus.SAVED)
        now = utc_now_iso()
        if existing:
            rec = existing
            rec.status = status
            rec.role = package.job_title
            rec.company = package.company
            rec.resume_version = package.tailored_resume_id
            rec.cover_letter_version = package.package_id
            rec.recruiter_message_version = package.package_id
            rec.last_action_at = now
            rec.recommendation_snapshot = dict(package.recommendation_snapshot)
            if status == ApplicationStatus.EXPORTED and not rec.applied_at:
                rec.pipeline_state = CompanyPipelineState.ACTIVE
        else:
            rec = ApplicationRecord(
                application_id=str(uuid.uuid4()),
                package_id=package.package_id,
                job_id=package.source_job_id,
                company=package.company,
                role=package.job_title,
                status=status,
                resume_version=package.tailored_resume_id,
                cover_letter_version=package.package_id,
                recruiter_message_version=package.package_id,
                created_at=now,
                updated_at=now,
                last_action_at=now,
                recommendation_snapshot=dict(package.recommendation_snapshot),
                pipeline_state=CompanyPipelineState.ACTIVE,
            )
        return self.upsert(rec)

    def update_status(
        self,
        application_id: str,
        status: ApplicationStatus,
        *,
        notes: str = "",
        interview_stage: str | None = None,
    ) -> ApplicationRecord:
        rec = self.get(application_id)
        rec.status = status
        now = utc_now_iso()
        rec.last_action_at = now
        if notes:
            rec.notes = notes
        if status == ApplicationStatus.APPLIED:
            rec.applied_at = now
            rec.pipeline_state = CompanyPipelineState.ACTIVE
        if status == ApplicationStatus.REJECTED:
            rec.pipeline_state = CompanyPipelineState.CLOSED
        if interview_stage:
            from application_tracking.models import InterviewStage

            rec.interview_stage = InterviewStage(interview_stage)
        return self.upsert(rec)
