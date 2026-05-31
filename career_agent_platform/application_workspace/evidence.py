"""Verified resume evidence extraction — no fabrication."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from recommendation_engine import RecommendationResult

_BULLET_RE = re.compile(r"^[\s]*(?:[•\-\*]|\d+\.)\s*(.+)$", re.MULTILINE)

_DIMENSION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "enterprise_governance": ("governance", "steering", "portfolio", "sdlc", "compliance"),
    "technical_execution": ("technical", "engineering", "sdlc", "ci/cd", "architecture review"),
    "transformation_strategy": ("transformation", "operating model", "change", "migration"),
    "ai_strategy": ("genai", "ai ", "machine learning", "data science"),
    "delivery_execution": ("delivery", "program", "release train", "dependency"),
    "stakeholder_complexity": ("stakeholder", "executive", "c-suite", "client", "fortune"),
    "organizational_leadership": ("led ", "managed", "directed", "teams"),
    "release_governance": ("release", "pi planning", "deployment", "cutover", "safe"),
    "architecture_coordination": ("architecture", "cloud", "aws", "infrastructure"),
    "portfolio_management": ("portfolio", "budget", "benefits"),
    "executive_communication": ("executive", "steering committee", "reporting"),
}

_EXCLUSION_RULES: list[tuple[str, float, str]] = [
    ("architecture_coordination", 0.35, "Cloud architecture ownership intentionally excluded due to insufficient evidence."),
    ("ai_strategy", 0.30, "AI strategy claims intentionally excluded due to insufficient evidence."),
    ("product_thinking", 0.35, "Product roadmap ownership intentionally excluded due to insufficient evidence."),
    ("operational_management", 0.40, "Operations management emphasis intentionally excluded due to insufficient evidence."),
]


@dataclass
class VerifiedEvidence:
    """Resume lines and topics backed by parsed resume text only."""

    resume_lines: list[str] = field(default_factory=list)
    evidence_snippets: list[str] = field(default_factory=list)
    matched_capabilities: list[str] = field(default_factory=list)
    excluded_topics: list[str] = field(default_factory=list)
    exclusion_explanations: list[str] = field(default_factory=list)

    def all_evidence_labels(self) -> list[str]:
        return list(self.evidence_snippets)


def _resume_bullets(resume_text: str) -> list[str]:
    lines: list[str] = []
    for raw in resume_text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        m = _BULLET_RE.match(stripped)
        if m:
            lines.append(m.group(1).strip())
        elif stripped.startswith("•") or stripped.startswith("-"):
            lines.append(stripped.lstrip("•-* ").strip())
    return lines


def _line_matches_keywords(line: str, keywords: tuple[str, ...]) -> bool:
    lower = line.lower()
    return any(kw in lower for kw in keywords)


def extract_verified_evidence(
    resume_text: str,
    recommendation: RecommendationResult,
) -> VerifiedEvidence:
    """Map recommendation strengths to resume bullets present in source text."""
    bullets = _resume_bullets(resume_text)
    if not bullets:
        for line in resume_text.splitlines():
            s = line.strip()
            if len(s) > 20 and not s.upper() == s:
                bullets.append(s)

    match_detail = recommendation.match_detail or {}
    dominant = list(recommendation.dominant_dimensions or [])
    if not dominant:
        dominant = list(match_detail.get("dominant_match_dimensions") or [])

    evidence: list[str] = []
    matched_caps: list[str] = []

    for dim in dominant[:6]:
        keywords = _DIMENSION_KEYWORDS.get(dim, (dim.replace("_", " "),))
        for bullet in bullets:
            if _line_matches_keywords(bullet, keywords) and bullet not in evidence:
                evidence.append(bullet)
                matched_caps.append(dim)
                break

    for strength in recommendation.top_strengths[:4]:
        for bullet in bullets:
            if any(tok in bullet.lower() for tok in strength.lower().split()[:3] if len(tok) > 4):
                if bullet not in evidence:
                    evidence.append(bullet)
                break

    excluded: list[str] = []
    exclusions: list[str] = []
    for dim_key, threshold, msg in _EXCLUSION_RULES:
        fit_key = {
            "architecture_coordination": "architecture_fit",
            "ai_strategy": "transformation_fit",
            "product_thinking": "capability_similarity",
            "operational_management": "eligibility_fit",
        }.get(dim_key, "")
        score = float(match_detail.get(fit_key, 1.0)) if fit_key else 1.0
        if score < threshold:
            excluded.append(dim_key)
            exclusions.append(msg)

    if match_detail.get("is_architecture_heavy") and float(match_detail.get("architecture_fit", 0)) < 0.40:
        msg = "Cloud architecture ownership intentionally excluded due to insufficient evidence."
        if msg not in exclusions:
            exclusions.append(msg)

    if match_detail.get("is_release_governance_heavy"):
        for bullet in bullets:
            if _line_matches_keywords(bullet, _DIMENSION_KEYWORDS["release_governance"]):
                if bullet not in evidence:
                    evidence.append(bullet)
        if not any("release governance" in e.lower() for e in exclusions):
            exclusions.append(
                "Generated from verified release governance and TPM evidence already present in the resume.",
            )

    return VerifiedEvidence(
        resume_lines=bullets,
        evidence_snippets=evidence[:8],
        matched_capabilities=list(dict.fromkeys(matched_caps)),
        excluded_topics=excluded,
        exclusion_explanations=exclusions,
    )


def tailored_resume_id(job_id: str, resume_text: str) -> str:
    digest = hashlib.sha256(f"{job_id}:{resume_text}".encode("utf-8")).hexdigest()[:16]
    return f"tailored_{job_id}_{digest}"
