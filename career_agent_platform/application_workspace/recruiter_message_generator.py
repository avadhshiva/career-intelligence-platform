"""Deterministic recruiter outreach messages — concise, executive, non-spammy."""

from __future__ import annotations

from application_workspace.evidence import VerifiedEvidence
from application_workspace.models import RecruiterMessage
from recommendation_engine import RecommendationResult


def _top_capability_phrase(evidence: VerifiedEvidence, rec: RecommendationResult) -> str:
    if evidence.evidence_snippets:
        short = evidence.evidence_snippets[0]
        if len(short) > 90:
            short = short[:87] + "..."
        return short
    if rec.top_strengths:
        line = rec.top_strengths[0]
        if "job weight" in line.lower():
            return line.split("(")[0].strip() or line
        return line
    summary = (rec.recruiter_summary or "").strip()
    if summary and len(summary) <= 120:
        return summary
    return "enterprise program delivery and cross-functional governance"


def generate_recruiter_messages(
    resume_text: str,
    recommendation: RecommendationResult,
    evidence: VerifiedEvidence,
) -> RecruiterMessage:
    """LinkedIn intro, hiring-manager note, and referral request variants."""
    name = resume_text.strip().splitlines()[0].split("|")[0].strip() if resume_text.strip() else "I"
    capability = _top_capability_phrase(evidence, recommendation)
    role = recommendation.job_title
    company = recommendation.company

    linkedin = (
        f"Hi — I am {name}, exploring the {role} opportunity at {company}. "
        f"My background includes {capability.rstrip('.')}. "
        f"I believe there is meaningful alignment with your team's priorities and "
        f"would welcome a brief conversation if you are the right contact. "
        f"Happy to work around your schedule."
    )

    hiring_manager = (
        f"Subject: {role} — brief introduction\n\n"
        f"I am interested in the {role} position at {company}. "
        f"Verified strengths for your team include {capability.rstrip('.')}. "
        f"I lead with governance-aware program delivery and transparent executive reporting. "
        f"Happy to share a tailored resume and discuss fit in a 20-minute call."
    )

    referral = (
        f"Hello — I am exploring the {role} role at {company} and wondered if you might "
        f"consider a referral or warm introduction. My resume documents {capability.rstrip('.')}; "
        f"I am not asking for endorsement beyond what you are comfortable attesting. "
        f"Thank you for any guidance."
    )

    explanation = list(evidence.exclusion_explanations)
    explanation.append(
        "Messages use only verified resume snippets; no fabricated metrics or tools.",
    )

    evidence_labels = [
        f"Resume bullet: {s[:70]}..." if len(s) > 70 else f"Resume bullet: {s}"
        for s in evidence.evidence_snippets[:3]
    ]

    return RecruiterMessage(
        linkedin_intro=linkedin,
        hiring_manager_note=hiring_manager,
        referral_request=referral,
        generated_from_evidence=evidence_labels,
        confidence=recommendation.confidence,
        explanation=explanation,
    )
