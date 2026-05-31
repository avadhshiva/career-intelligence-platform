"""Plaintext formatting helpers for artifacts and exports."""

from __future__ import annotations

from application_workspace.models import ApplicationQualityScores, InterviewPrepSummary


def format_interview_prep(prep: InterviewPrepSummary) -> str:
    lines = ["INTERVIEW PREPARATION SUMMARY", ""]
    lines.append("Likely focus areas:")
    lines.extend(f"  • {a}" for a in prep.likely_focus_areas)
    lines.append("\nStrongest strengths:")
    lines.extend(f"  • {s}" for s in prep.strongest_strengths)
    lines.append("\nProbable gap questions:")
    lines.extend(f"  • {q}" for q in prep.probable_gap_questions)
    lines.append("\nPreparation topics:")
    lines.extend(f"  • {t}" for t in prep.preparation_topics)
    lines.append("\nRisk areas:")
    lines.extend(f"  • {r}" for r in prep.risk_areas)
    return "\n".join(lines)


def format_quality(quality: ApplicationQualityScores) -> str:
    return (
        f"Overall application quality: {quality.overall_application_quality_score:.0%}\n"
        f"Resume alignment: {quality.resume_alignment:.0%}\n"
        f"ATS readiness: {quality.ats_readiness:.0%}\n"
        f"Leadership fit: {quality.leadership_fit:.0%}\n"
        f"Keyword coverage: {quality.keyword_coverage:.0%}\n"
        f"Recruiter readability: {quality.recruiter_readability:.0%}\n"
        f"Completeness: {quality.application_completeness:.0%}"
    )
