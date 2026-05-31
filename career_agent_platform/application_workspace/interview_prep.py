"""Interview preparation summary from match engine outputs."""

from __future__ import annotations

from application_workspace.evidence import VerifiedEvidence
from application_workspace.models import InterviewPrepSummary
from recommendation_engine import RecommendationResult


def _focus_areas(rec: RecommendationResult, match: dict) -> list[str]:
    areas: list[str] = []
    if match.get("is_release_governance_heavy"):
        areas.append("Release governance, PI planning, and deployment readiness")
    if match.get("is_ai_transformation") or float(match.get("transformation_fit", 0)) >= 0.45:
        areas.append("Transformation roadmap and change leadership")
    if float(match.get("governance_fit", 0)) >= 0.45:
        areas.append("Portfolio governance and executive reporting")
    if float(match.get("technical_execution", 0)) >= 0.50 or float(
        match.get("capability_similarity", 0),
    ) >= 0.50:
        areas.append("Cross-functional technical delivery and dependency management")
    if match.get("is_architecture_heavy"):
        areas.append("Architecture coordination and platform migration trade-offs")
    if match.get("is_product_heavy"):
        areas.append("Product strategy, roadmap ownership, and customer discovery")
    if not areas:
        areas.append("Program delivery scope, stakeholder management, and risk mitigation")
    return areas[:5]


def generate_interview_prep(
    recommendation: RecommendationResult,
    evidence: VerifiedEvidence,
) -> InterviewPrepSummary:
    """Build interview prep from match gaps, strengths, and JD signals."""
    match = recommendation.match_detail or {}
    explanation: list[str] = []

    focus = _focus_areas(recommendation, match)
    strengths = list(recommendation.top_strengths[:5])
    if evidence.evidence_snippets and not strengths:
        strengths = [f"Verified: {s}" for s in evidence.evidence_snippets[:3]]

    gap_questions: list[str] = []
    for gap in recommendation.gaps[:4]:
        gap_questions.append(f"How would you address: {gap}?")
    for cap in recommendation.missing_capabilities[:3]:
        gap_questions.append(f"Tell me about your experience with {cap}.")

    prep_topics: list[str] = []
    for imp in match.get("recommended_resume_improvements") or []:
        prep_topics.append(f"Prepare narrative for: {imp}")
    if match.get("is_release_governance_heavy"):
        prep_topics.append("Steering committee examples and release calendar ownership")
        explanation.append(
            "Interview prep highlights portfolio governance because JD emphasizes executive reporting.",
        )
    if float(match.get("transformation_fit", 0)) >= 0.40:
        prep_topics.append("Transformation outcomes with measurable scope from resume only")

    risks = list(recommendation.top_risks[:4]) or list(recommendation.risks[:4])
    for dim in recommendation.missing_dimensions[:3]:
        risks.append(f"Gap dimension: {dim}")
    if not gap_questions and recommendation.missing_capabilities:
        for cap in recommendation.missing_capabilities[:2]:
            gap_questions.append(f"How have you applied {cap} in prior roles?")
    if not gap_questions:
        gap_questions.append(
            "Walk me through a recent program where you owned governance cadence end-to-end.",
        )
    if not risks and float(match.get("confidence", 1.0)) < 0.99:
        risks.append(
            "Validate depth on any dimension below competitive threshold before final round.",
        )

    if match.get("is_architecture_heavy") and float(match.get("architecture_fit", 0)) < 0.40:
        explanation.append(
            "Cloud architecture ownership intentionally excluded due to insufficient evidence.",
        )
        risks.append("Architecture depth — expect probing questions; stay within resume evidence.")

    explanation.append(
        "Interview prep derived from role fit assessment and verified resume bullets only.",
    )

    evidence_labels = [
        f"Match strength: {s}" for s in strengths[:3]
    ] + [f"Gap signal: {g}" for g in recommendation.gaps[:2]]

    return InterviewPrepSummary(
        likely_focus_areas=focus,
        strongest_strengths=strengths,
        probable_gap_questions=gap_questions[:6],
        preparation_topics=prep_topics[:6],
        risk_areas=risks[:6],
        generated_from_evidence=evidence_labels,
        confidence=recommendation.confidence,
        explanation=explanation,
    )
