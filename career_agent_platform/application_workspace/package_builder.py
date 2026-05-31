"""Orchestrates full application package generation."""

from __future__ import annotations

from application_workspace.application_quality import compute_application_quality
from application_workspace.cover_letter_generator import generate_cover_letter
from application_workspace.evidence import extract_verified_evidence, tailored_resume_id
from application_workspace.interview_prep import generate_interview_prep
from application_workspace.models import (
    ApplicationApprovalState,
    ApplicationArtifact,
    ApplicationArtifactType,
    ApplicationPackage,
    utc_now_iso,
)
from application_workspace.recruiter_message_generator import generate_recruiter_messages
from application_workspace.review_manager import ApplicationReviewManager
from application_workspace.formatting import format_interview_prep, format_quality
from application_workspace.tailored_resume import build_tailored_resume
from monitoring.ops_log import log_event, timed_operation
from recommendation_engine import RecommendationResult


class ApplicationPackageBuilder:
    """Build recruiter-ready packages from approved recommendations + base resume."""

    def __init__(self, review_manager: ApplicationReviewManager | None = None) -> None:
        self._review = review_manager or ApplicationReviewManager()

    def build(
        self,
        recommendation: RecommendationResult,
        base_resume_text: str,
        *,
        package_id: str | None = None,
        persist: bool = True,
    ) -> ApplicationPackage:
        job_id = recommendation.job_id
        with timed_operation(
            "package_generation",
            job_id=job_id,
            persist=persist,
        ):
            return self._build_inner(
                recommendation,
                base_resume_text,
                package_id=package_id,
                persist=persist,
            )

    def _build_inner(
        self,
        recommendation: RecommendationResult,
        base_resume_text: str,
        *,
        package_id: str | None = None,
        persist: bool = True,
    ) -> ApplicationPackage:
        tid = tailored_resume_id(recommendation.job_id, base_resume_text)
        tailored = build_tailored_resume(
            base_resume_text,
            recommendation,
            tailored_id=tid,
        )
        evidence = extract_verified_evidence(base_resume_text, recommendation)
        cover = generate_cover_letter(base_resume_text, recommendation, evidence)
        recruiter = generate_recruiter_messages(base_resume_text, recommendation, evidence)
        prep = generate_interview_prep(recommendation, evidence)
        quality = compute_application_quality(
            recommendation,
            evidence,
            cover_letter=cover,
            interview_prep=prep,
            tailored_resume_text=tailored.text,
        )

        pkg_id = package_id or self._review.create_package_id()
        all_evidence = evidence.all_evidence_labels()
        explanation = list(evidence.exclusion_explanations)
        explanation.extend(quality.explanation)

        artifacts = [
            ApplicationArtifact(
                artifact_type=ApplicationArtifactType.TAILORED_RESUME,
                content=tailored.text,
                generated_from_evidence=all_evidence,
                confidence=recommendation.confidence,
                explanation=tailored.explanation,
            ),
            ApplicationArtifact(
                artifact_type=ApplicationArtifactType.COVER_LETTER,
                content=cover.body,
                generated_from_evidence=cover.generated_from_evidence,
                confidence=cover.confidence,
                explanation=cover.explanation,
            ),
            ApplicationArtifact(
                artifact_type=ApplicationArtifactType.RECRUITER_LINKEDIN,
                content=recruiter.linkedin_intro,
                generated_from_evidence=recruiter.generated_from_evidence,
                confidence=recruiter.confidence,
                explanation=recruiter.explanation,
            ),
            ApplicationArtifact(
                artifact_type=ApplicationArtifactType.RECRUITER_HIRING_MANAGER,
                content=recruiter.hiring_manager_note,
                generated_from_evidence=recruiter.generated_from_evidence,
                confidence=recruiter.confidence,
                explanation=recruiter.explanation,
            ),
            ApplicationArtifact(
                artifact_type=ApplicationArtifactType.RECRUITER_REFERRAL,
                content=recruiter.referral_request,
                generated_from_evidence=recruiter.generated_from_evidence,
                confidence=recruiter.confidence,
                explanation=recruiter.explanation,
            ),
            ApplicationArtifact(
                artifact_type=ApplicationArtifactType.INTERVIEW_PREP,
                content=format_interview_prep(prep),
                generated_from_evidence=prep.generated_from_evidence,
                confidence=prep.confidence,
                explanation=prep.explanation,
            ),
            ApplicationArtifact(
                artifact_type=ApplicationArtifactType.QUALITY_REPORT,
                content=format_quality(quality),
                generated_from_evidence=all_evidence,
                confidence=quality.confidence,
                explanation=quality.explanation,
            ),
        ]

        snap = recommendation.to_dict()
        snap["gaps"] = list(recommendation.gaps)
        snap["risks"] = list(recommendation.risks)

        package = ApplicationPackage(
            package_id=pkg_id,
            source_job_id=recommendation.job_id,
            tailored_resume_id=tailored.tailored_resume_id,
            job_title=recommendation.job_title,
            company=recommendation.company,
            generated_at=utc_now_iso(),
            generated_from_evidence=all_evidence,
            confidence=recommendation.confidence,
            approval_status=ApplicationApprovalState.GENERATED,
            explanation=explanation,
            tailored_resume_text=tailored.text,
            cover_letter=cover,
            recruiter_message=recruiter,
            interview_prep=prep,
            quality_scores=quality,
            artifacts=artifacts,
            recommendation_snapshot=snap,
        )
        package = self._review.record_initial_state(package)

        if persist:
            self._review.save_package(package)
        log_event(
            "package_generation_saved",
            job_id=recommendation.job_id,
            package_id=package.package_id,
            persist=persist,
        )
        return package
