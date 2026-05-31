"""Deterministic cover letter generation from verified resume evidence."""

from __future__ import annotations

from application_workspace.evidence import VerifiedEvidence
from application_workspace.models import CoverLetterResult
from recommendation_engine import RecommendationResult

_GOVERNANCE_PHRASES = ("governance", "release", "steering", "portfolio", "sdlc")
_TRANSFORMATION_PHRASES = ("transformation", "migration", "operating model", "genai", "change")


def _candidate_name(resume_text: str) -> str:
    first = resume_text.strip().splitlines()[0] if resume_text.strip() else "Candidate"
    if "|" in first:
        return first.split("|")[0].strip()
    return first.strip()[:60]


def _emphasis_clause(evidence: VerifiedEvidence, rec: RecommendationResult) -> str:
    snippets = evidence.evidence_snippets[:3]
    if snippets:
        joined = "; ".join(snippets[:2])
        return (
            f"My background includes verified experience such as: {joined}. "
        )
    if rec.top_strengths:
        return (
            f"My strongest verified capabilities for this role include "
            f"{rec.top_strengths[0].lower()}. "
        )
    return "My experience aligns with the program delivery and governance needs described in the role. "


def _governance_alignment(evidence: VerifiedEvidence, rec: RecommendationResult) -> str:
    match = rec.match_detail or {}
    if match.get("is_release_governance_heavy") or float(match.get("governance_fit", 0)) >= 0.45:
        if any(any(p in s.lower() for p in _GOVERNANCE_PHRASES) for s in evidence.evidence_snippets):
            return (
                "I bring release governance and executive reporting discipline grounded in "
                "evidence already documented on my resume. "
            )
    return ""


def _transformation_alignment(evidence: VerifiedEvidence, rec: RecommendationResult) -> str:
    match = rec.match_detail or {}
    if match.get("is_ai_transformation") or float(match.get("transformation_fit", 0)) >= 0.40:
        if any(any(p in s.lower() for p in _TRANSFORMATION_PHRASES) for s in evidence.evidence_snippets):
            return (
                "I have led transformation-oriented delivery with verifiable program outcomes "
                "described in my resume, without overstating scope beyond that evidence. "
            )
    return ""


def generate_cover_letter(
    resume_text: str,
    recommendation: RecommendationResult,
    evidence: VerifiedEvidence,
) -> CoverLetterResult:
    """Build a short professional cover letter using only verified evidence."""
    name = _candidate_name(resume_text)
    explanation: list[str] = list(evidence.exclusion_explanations)
    positioning = (recommendation.recruiter_summary or "").strip()
    if positioning:
        fit_lead = positioning.split(".")[0].rstrip(".") + "."
    else:
        fit_lead = (
            "My documented experience aligns with the delivery and governance "
            "themes described in the role."
        )

    opening = (
        f"Dear Hiring Team,\n\n"
        f"I am writing to express interest in the {recommendation.job_title} role at "
        f"{recommendation.company}. {fit_lead}\n\n"
    )

    fit = (
        f"{_emphasis_clause(evidence, recommendation)}"
        f"I am well suited because my verified track record maps to your stated needs in "
        f"{recommendation.recruiter_summary or 'cross-functional technical program delivery'}."
    )

    leadership = ""
    if float(recommendation.match_detail.get("governance_fit", 0)) >= 0.40:
        leadership = (
            "\n\nFrom a leadership and governance perspective, I have operated with "
            "steering-level stakeholders and structured delivery cadences reflected in my resume."
        )
        explanation.append(
            "Leadership/governance alignment drawn from governance_fit and verified steering evidence.",
        )

    gov = _governance_alignment(evidence, recommendation)
    trans = _transformation_alignment(evidence, recommendation)
    if gov:
        explanation.append(
            "Generated from verified release governance and TPM evidence already present in the resume.",
        )
    if trans:
        explanation.append(
            "Transformation/program delivery alignment uses only resume-documented transformation bullets.",
        )

    close = (
        "\n\nI would welcome a conversation to discuss how my documented experience can support "
        f"your team. Thank you for your consideration.\n\nSincerely,\n{name}"
    )

    body = opening + fit + leadership + ("\n\n" + gov if gov else "") + ("\n\n" + trans if trans else "") + close

    evidence_labels = [
        f"Resume bullet: {s[:80]}..." if len(s) > 80 else f"Resume bullet: {s}"
        for s in evidence.evidence_snippets[:5]
    ]

    return CoverLetterResult(
        body=body,
        generated_from_evidence=evidence_labels,
        confidence=min(0.95, recommendation.confidence + 0.05),
        explanation=explanation,
    )
