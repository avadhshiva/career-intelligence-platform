"""Application package workspace data models — Phase 5C."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ApplicationApprovalState(str, Enum):
    GENERATED = "generated"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"
    ARCHIVED = "archived"
    REOPENED = "reopened"


@dataclass
class StateHistoryEntry:
    """Timestamped lifecycle transition or blocked attempt."""

    from_state: str
    to_state: str
    timestamp: str
    review_notes: str = ""
    reviewer_action_reason: str = ""
    success: bool = True
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "timestamp": self.timestamp,
            "review_notes": self.review_notes,
            "reviewer_action_reason": self.reviewer_action_reason,
            "success": self.success,
            "warning": self.warning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateHistoryEntry:
        return cls(
            from_state=str(data.get("from_state", "")),
            to_state=str(data.get("to_state", "")),
            timestamp=str(data.get("timestamp", "")),
            review_notes=str(data.get("review_notes", "")),
            reviewer_action_reason=str(data.get("reviewer_action_reason", "")),
            success=bool(data.get("success", True)),
            warning=str(data.get("warning", "")),
        )


class ApplicationArtifactType(str, Enum):
    COVER_LETTER = "cover_letter"
    RECRUITER_LINKEDIN = "recruiter_linkedin"
    RECRUITER_HIRING_MANAGER = "recruiter_hiring_manager"
    RECRUITER_REFERRAL = "recruiter_referral"
    INTERVIEW_PREP = "interview_prep"
    TAILORED_RESUME = "tailored_resume"
    QUALITY_REPORT = "quality_report"


@dataclass
class ApplicationArtifact:
    """Single explainable artifact in an application package."""

    artifact_type: ApplicationArtifactType
    content: str
    generated_from_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    explanation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": self.artifact_type.value,
            "content": self.content,
            "generated_from_evidence": list(self.generated_from_evidence),
            "confidence": self.confidence,
            "explanation": list(self.explanation),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApplicationArtifact:
        return cls(
            artifact_type=ApplicationArtifactType(data["artifact_type"]),
            content=str(data.get("content", "")),
            generated_from_evidence=list(data.get("generated_from_evidence") or []),
            confidence=float(data.get("confidence", 0.0)),
            explanation=list(data.get("explanation") or []),
        )


@dataclass
class CoverLetterResult:
    body: str
    generated_from_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    explanation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body,
            "generated_from_evidence": list(self.generated_from_evidence),
            "confidence": self.confidence,
            "explanation": list(self.explanation),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoverLetterResult:
        return cls(
            body=str(data.get("body", "")),
            generated_from_evidence=list(data.get("generated_from_evidence") or []),
            confidence=float(data.get("confidence", 0.0)),
            explanation=list(data.get("explanation") or []),
        )


@dataclass
class RecruiterMessage:
    linkedin_intro: str
    hiring_manager_note: str
    referral_request: str
    generated_from_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    explanation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "linkedin_intro": self.linkedin_intro,
            "hiring_manager_note": self.hiring_manager_note,
            "referral_request": self.referral_request,
            "generated_from_evidence": list(self.generated_from_evidence),
            "confidence": self.confidence,
            "explanation": list(self.explanation),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecruiterMessage:
        return cls(
            linkedin_intro=str(data.get("linkedin_intro", "")),
            hiring_manager_note=str(data.get("hiring_manager_note", "")),
            referral_request=str(data.get("referral_request", "")),
            generated_from_evidence=list(data.get("generated_from_evidence") or []),
            confidence=float(data.get("confidence", 0.0)),
            explanation=list(data.get("explanation") or []),
        )


@dataclass
class InterviewPrepSummary:
    likely_focus_areas: list[str] = field(default_factory=list)
    strongest_strengths: list[str] = field(default_factory=list)
    probable_gap_questions: list[str] = field(default_factory=list)
    preparation_topics: list[str] = field(default_factory=list)
    risk_areas: list[str] = field(default_factory=list)
    generated_from_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    explanation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "likely_focus_areas": list(self.likely_focus_areas),
            "strongest_strengths": list(self.strongest_strengths),
            "probable_gap_questions": list(self.probable_gap_questions),
            "preparation_topics": list(self.preparation_topics),
            "risk_areas": list(self.risk_areas),
            "generated_from_evidence": list(self.generated_from_evidence),
            "confidence": self.confidence,
            "explanation": list(self.explanation),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterviewPrepSummary:
        return cls(
            likely_focus_areas=list(data.get("likely_focus_areas") or []),
            strongest_strengths=list(data.get("strongest_strengths") or []),
            probable_gap_questions=list(data.get("probable_gap_questions") or []),
            preparation_topics=list(data.get("preparation_topics") or []),
            risk_areas=list(data.get("risk_areas") or []),
            generated_from_evidence=list(data.get("generated_from_evidence") or []),
            confidence=float(data.get("confidence", 0.0)),
            explanation=list(data.get("explanation") or []),
        )


@dataclass
class ApplicationQualityScores:
    resume_alignment: float = 0.0
    ats_readiness: float = 0.0
    leadership_fit: float = 0.0
    keyword_coverage: float = 0.0
    confidence: float = 0.0
    recruiter_readability: float = 0.0
    application_completeness: float = 0.0
    overall_application_quality_score: float = 0.0
    explanation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resume_alignment": self.resume_alignment,
            "ats_readiness": self.ats_readiness,
            "leadership_fit": self.leadership_fit,
            "keyword_coverage": self.keyword_coverage,
            "confidence": self.confidence,
            "recruiter_readability": self.recruiter_readability,
            "application_completeness": self.application_completeness,
            "overall_application_quality_score": self.overall_application_quality_score,
            "explanation": list(self.explanation),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApplicationQualityScores:
        return cls(
            resume_alignment=float(data.get("resume_alignment", 0.0)),
            ats_readiness=float(data.get("ats_readiness", 0.0)),
            leadership_fit=float(data.get("leadership_fit", 0.0)),
            keyword_coverage=float(data.get("keyword_coverage", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            recruiter_readability=float(data.get("recruiter_readability", 0.0)),
            application_completeness=float(data.get("application_completeness", 0.0)),
            overall_application_quality_score=float(
                data.get("overall_application_quality_score", 0.0),
            ),
            explanation=list(data.get("explanation") or []),
        )


@dataclass
class ApplicationPackage:
    """Complete recruiter-ready application package for human approval."""

    package_id: str
    source_job_id: str
    tailored_resume_id: str
    job_title: str = ""
    company: str = ""
    generated_at: str = ""
    generated_from_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    approval_status: ApplicationApprovalState = ApplicationApprovalState.GENERATED
    explanation: list[str] = field(default_factory=list)
    tailored_resume_text: str = ""
    cover_letter: CoverLetterResult | None = None
    recruiter_message: RecruiterMessage | None = None
    interview_prep: InterviewPrepSummary | None = None
    quality_scores: ApplicationQualityScores | None = None
    artifacts: list[ApplicationArtifact] = field(default_factory=list)
    reviewer_notes: str = ""
    rejection_reason: str = ""
    state_history: list[StateHistoryEntry] = field(default_factory=list)
    recommendation_snapshot: dict[str, Any] = field(default_factory=dict)
    last_warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "source_job_id": self.source_job_id,
            "tailored_resume_id": self.tailored_resume_id,
            "job_title": self.job_title,
            "company": self.company,
            "generated_at": self.generated_at,
            "generated_from_evidence": list(self.generated_from_evidence),
            "confidence": self.confidence,
            "approval_status": self.approval_status.value,
            "explanation": list(self.explanation),
            "tailored_resume_text": self.tailored_resume_text,
            "cover_letter": self.cover_letter.to_dict() if self.cover_letter else None,
            "recruiter_message": (
                self.recruiter_message.to_dict() if self.recruiter_message else None
            ),
            "interview_prep": self.interview_prep.to_dict() if self.interview_prep else None,
            "quality_scores": self.quality_scores.to_dict() if self.quality_scores else None,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "reviewer_notes": self.reviewer_notes,
            "rejection_reason": self.rejection_reason,
            "state_history": [h.to_dict() for h in self.state_history],
            "recommendation_snapshot": dict(self.recommendation_snapshot),
            "last_warning": self.last_warning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApplicationPackage:
        cover = data.get("cover_letter")
        recruiter = data.get("recruiter_message")
        prep = data.get("interview_prep")
        quality = data.get("quality_scores")
        return cls(
            package_id=str(data["package_id"]),
            source_job_id=str(data["source_job_id"]),
            tailored_resume_id=str(data["tailored_resume_id"]),
            job_title=str(data.get("job_title", "")),
            company=str(data.get("company", "")),
            generated_at=str(data.get("generated_at", "")),
            generated_from_evidence=list(data.get("generated_from_evidence") or []),
            confidence=float(data.get("confidence", 0.0)),
            approval_status=ApplicationApprovalState(
                data.get("approval_status", ApplicationApprovalState.GENERATED.value),
            ),
            explanation=list(data.get("explanation") or []),
            tailored_resume_text=str(data.get("tailored_resume_text", "")),
            cover_letter=CoverLetterResult.from_dict(cover) if cover else None,
            recruiter_message=RecruiterMessage.from_dict(recruiter) if recruiter else None,
            interview_prep=InterviewPrepSummary.from_dict(prep) if prep else None,
            quality_scores=ApplicationQualityScores.from_dict(quality) if quality else None,
            artifacts=[
                ApplicationArtifact.from_dict(a) for a in (data.get("artifacts") or [])
            ],
            reviewer_notes=str(data.get("reviewer_notes", "")),
            rejection_reason=str(data.get("rejection_reason", "")),
            state_history=[
                StateHistoryEntry.from_dict(h) for h in (data.get("state_history") or [])
            ],
            recommendation_snapshot=dict(data.get("recommendation_snapshot") or {}),
            last_warning=str(data.get("last_warning", "")),
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
