"""Deterministic resume tailoring — reorder verified bullets only, no fabrication."""

from __future__ import annotations

from dataclasses import dataclass, field

from application_workspace.evidence import VerifiedEvidence, extract_verified_evidence
from recommendation_engine import RecommendationResult


@dataclass
class TailoredResumeResult:
    tailored_resume_id: str
    text: str
    change_log: list[str] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)


def _score_line(line: str, evidence: VerifiedEvidence, rec: RecommendationResult) -> int:
    score = 0
    lower = line.lower()
    if line in evidence.evidence_snippets:
        score += 10
    for cap in evidence.matched_capabilities:
        for kw in cap.replace("_", " ").split():
            if len(kw) > 3 and kw in lower:
                score += 2
    for strength in rec.top_strengths:
        for tok in strength.lower().split():
            if len(tok) > 4 and tok in lower:
                score += 1
    return score


def build_tailored_resume(
    base_resume_text: str,
    recommendation: RecommendationResult,
    *,
    tailored_id: str,
) -> TailoredResumeResult:
    """Produce a role-targeted resume using only original resume content."""
    evidence = extract_verified_evidence(base_resume_text, recommendation)
    lines = base_resume_text.splitlines()
    header: list[str] = []
    body: list[str] = []
    in_body = False

    for line in lines:
        if not in_body and (line.strip().startswith("•") or line.strip().startswith("-")):
            in_body = True
        if not in_body:
            header.append(line)
        else:
            body.append(line)

    if body:
        ranked = sorted(body, key=lambda ln: -_score_line(ln, evidence, recommendation))
        tailored_body = ranked
    else:
        tailored_body = lines

    banner = (
        f"--- Tailored for: {recommendation.job_title} @ {recommendation.company} "
        f"(deterministic emphasis; no new claims) ---"
    )
    text = "\n".join([*header, banner, *tailored_body]) if header else "\n".join([banner, *tailored_body])

    change_log = [
        "Reordered existing resume bullets by verified match to role dimensions.",
        "No new metrics, projects, tools, or certifications were added.",
    ]
    explanation = list(evidence.exclusion_explanations)
    if evidence.evidence_snippets:
        explanation.append(
            "Generated from verified resume evidence aligned to dominant match dimensions.",
        )

    return TailoredResumeResult(
        tailored_resume_id=tailored_id,
        text=text,
        change_log=change_log,
        explanation=explanation,
    )
