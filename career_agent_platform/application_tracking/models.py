"""Application tracker data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPROVED = "approved"
    EXPORTED = "exported"
    APPLIED = "applied"
    RECRUITER_CONTACTED = "recruiter_contacted"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class InterviewStage(str, Enum):
    NONE = "none"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    PANEL = "panel"
    EXECUTIVE = "executive"
    FINAL = "final"


class CompanyPipelineState(str, Enum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    STALE = "stale"
    CLOSED = "closed"


@dataclass
class FollowUpNote:
    due_date: str
    action: str
    reason: str
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "due_date": self.due_date,
            "action": self.action,
            "reason": self.reason,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FollowUpNote:
        return cls(
            due_date=str(data.get("due_date", "")),
            action=str(data.get("action", "")),
            reason=str(data.get("reason", "")),
            created_at=str(data.get("created_at", "")),
        )


@dataclass
class ApplicationRecord:
    application_id: str
    package_id: str
    job_id: str
    company: str
    role: str
    status: ApplicationStatus = ApplicationStatus.SAVED
    interview_stage: InterviewStage = InterviewStage.NONE
    pipeline_state: CompanyPipelineState = CompanyPipelineState.UNKNOWN
    resume_version: str = ""
    cover_letter_version: str = ""
    recruiter_message_version: str = ""
    created_at: str = ""
    updated_at: str = ""
    applied_at: str = ""
    last_action_at: str = ""
    notes: str = ""
    followups: list[FollowUpNote] = field(default_factory=list)
    recommendation_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "package_id": self.package_id,
            "job_id": self.job_id,
            "company": self.company,
            "role": self.role,
            "status": self.status.value,
            "interview_stage": self.interview_stage.value,
            "pipeline_state": self.pipeline_state.value,
            "resume_version": self.resume_version,
            "cover_letter_version": self.cover_letter_version,
            "recruiter_message_version": self.recruiter_message_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "applied_at": self.applied_at,
            "last_action_at": self.last_action_at,
            "notes": self.notes,
            "followups": [f.to_dict() for f in self.followups],
            "recommendation_snapshot": dict(self.recommendation_snapshot),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApplicationRecord:
        return cls(
            application_id=str(data["application_id"]),
            package_id=str(data.get("package_id", "")),
            job_id=str(data.get("job_id", "")),
            company=str(data.get("company", "")),
            role=str(data.get("role", "")),
            status=ApplicationStatus(data.get("status", ApplicationStatus.SAVED.value)),
            interview_stage=InterviewStage(
                data.get("interview_stage", InterviewStage.NONE.value),
            ),
            pipeline_state=CompanyPipelineState(
                data.get("pipeline_state", CompanyPipelineState.UNKNOWN.value),
            ),
            resume_version=str(data.get("resume_version", "")),
            cover_letter_version=str(data.get("cover_letter_version", "")),
            recruiter_message_version=str(data.get("recruiter_message_version", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            applied_at=str(data.get("applied_at", "")),
            last_action_at=str(data.get("last_action_at", "")),
            notes=str(data.get("notes", "")),
            followups=[FollowUpNote.from_dict(f) for f in (data.get("followups") or [])],
            recommendation_snapshot=dict(data.get("recommendation_snapshot") or {}),
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
