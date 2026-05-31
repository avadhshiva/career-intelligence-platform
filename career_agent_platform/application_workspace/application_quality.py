"""Application package quality scoring — deterministic composite score."""

from __future__ import annotations

from application_workspace.evidence import VerifiedEvidence
from application_workspace.models import ApplicationQualityScores, CoverLetterResult, InterviewPrepSummary
from recommendation_engine import RecommendationResult


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_application_quality(
    recommendation: RecommendationResult,
    evidence: VerifiedEvidence,
    *,
    cover_letter: CoverLetterResult | None = None,
    interview_prep: InterviewPrepSummary | None = None,
    tailored_resume_text: str = "",
) -> ApplicationQualityScores:
    """Compute recruiter-facing quality dimensions and overall score."""
    match = recommendation.match_detail or {}
    explanation: list[str] = []

    resume_alignment = _clamp(recommendation.overall_match)
    explanation.append(f"Resume alignment sourced from overall_match ({resume_alignment:.0%}).")

    ats_readiness = _clamp(
        0.35
        + 0.25 * float(match.get("capability_similarity", 0))
        + 0.20 * (1.0 if recommendation.eligibility_passed else 0.0)
        + 0.10 * min(1.0, len(evidence.evidence_snippets) / 4.0),
    )

    leadership_fit = _clamp(
        0.55 * float(match.get("governance_fit", 0))
        + 0.25 * float(match.get("seniority_fit", 0))
        + 0.20 * float(match.get("eligibility_fit", 0)),
    )
    if float(match.get("governance_fit", 0)) >= 0.45:
        explanation.append("Leadership fit weighted toward governance_fit and seniority_fit.")

    keyword_hits = len(evidence.evidence_snippets) + len(recommendation.dominant_dimensions)
    keyword_coverage = _clamp(keyword_hits / 10.0)
    if recommendation.missing_capabilities:
        keyword_coverage = _clamp(keyword_coverage - 0.05 * len(recommendation.missing_capabilities))

    confidence = _clamp(recommendation.confidence)

    readability = _clamp(
        0.4
        + 0.2 * (1.0 if cover_letter and len(cover_letter.body) < 2500 else 0.5)
        + 0.2 * (1.0 if recommendation.recruiter_summary else 0.0)
        + 0.2 * min(1.0, len(recommendation.top_strengths) / 3.0),
    )

    completeness_parts = [
        bool(tailored_resume_text.strip()),
        bool(cover_letter and cover_letter.body.strip()),
        bool(interview_prep and interview_prep.likely_focus_areas),
        bool(recommendation.recruiter_summary),
    ]
    application_completeness = _clamp(sum(completeness_parts) / len(completeness_parts))

    overall = _clamp(
        0.22 * resume_alignment
        + 0.15 * ats_readiness
        + 0.18 * leadership_fit
        + 0.12 * keyword_coverage
        + 0.13 * confidence
        + 0.10 * readability
        + 0.10 * application_completeness,
    )

    explanation.append(
        f"Overall application quality score {overall:.0%} — weighted blend of alignment, ATS, "
        "leadership, keywords, confidence, readability, and completeness.",
    )

    return ApplicationQualityScores(
        resume_alignment=resume_alignment,
        ats_readiness=ats_readiness,
        leadership_fit=leadership_fit,
        keyword_coverage=keyword_coverage,
        confidence=confidence,
        recruiter_readability=readability,
        application_completeness=application_completeness,
        overall_application_quality_score=overall,
        explanation=explanation,
    )
