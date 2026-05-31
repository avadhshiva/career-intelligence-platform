"""Rank company opportunities against candidate profile."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from hiring_intelligence.company_mapper import COMPANY_PROFILES, CompanyProfile
from resume_routing.router import route_resume_for_family


def _family_score(profile: CandidateProfile, families: tuple[str, ...]) -> float:
    scores = profile.role_family_scores or {}
    if not scores:
        primary = profile.primary_career_track.value
        return 0.72 if primary in families else 0.35
    hits = [float(scores.get(f, 0.0)) for f in families]
    return min(1.0, sum(hits) / max(len(hits), 1))


def _dimension_score(profile: CandidateProfile, dimensions: tuple[str, ...]) -> float:
    vec = profile.capability_vector or {}
    hits = [float(vec.get(d, 0.0)) for d in dimensions]
    if not hits:
        return 0.4
    return min(1.0, sum(hits) / len(hits))


@dataclass
class OpportunityRecommendation:
    company: str
    role_family: str
    fit_score: float
    why_fit: list[str] = field(default_factory=list)
    recommended_resume: str = ""
    hiring_signals: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "role_family": self.role_family,
            "fit_score": self.fit_score,
            "why_fit": list(self.why_fit),
            "recommended_resume": self.recommended_resume,
            "hiring_signals": list(self.hiring_signals),
            "strengths": list(self.strengths),
            "risks": list(self.risks),
        }


def score_company_opportunity(
    profile: CandidateProfile,
    company: CompanyProfile,
) -> OpportunityRecommendation:
    family = company.typical_role_families[0]
    family_fit = _family_score(profile, company.typical_role_families)
    dim_fit = _dimension_score(profile, company.dominant_hiring_dimensions)
    gov_fit = min(1.0, profile.governance_experience * company.governance_intensity + 0.15)
    transform_fit = min(1.0, profile.transformation_focus * company.transformation_intensity + 0.10)

    fit = round((family_fit * 0.40 + dim_fit * 0.25 + gov_fit * 0.20 + transform_fit * 0.15) * 100, 1)

    why: list[str] = []
    if gov_fit >= 0.55:
        why.append("Strong enterprise governance overlap with this employer profile.")
    if transform_fit >= 0.55:
        why.append("AI workflow modernization and transformation alignment.")
    if family_fit >= 0.55:
        display = ROLE_FAMILIES.get(profile.primary_career_track)
        track = display.display_name if display else profile.primary_career_track.value.replace("_", " ").title()
        why.append(f"Your {track} track maps to their typical hiring families.")
    if not why:
        why.append("Moderate enterprise delivery similarity with this hiring profile.")

    strengths = [
        f"Governance intensity match ({int(company.governance_intensity * 100)}%)",
        f"Transformation intensity match ({int(company.transformation_intensity * 100)}%)",
    ]
    risks: list[str] = []
    ai = (profile.ai_maturity.value if profile.ai_maturity else "none").lower()
    if company.ai_maturity in {"transformation_lead", "practitioner"} and ai in {"none", "awareness"}:
        risks.append("Employer AI maturity may exceed current documented AI depth.")

    resume_label = route_resume_for_family(profile, family)
    hiring_signals = [
        f"Hiring momentum: {company.hiring_momentum}",
        f"Typical families: {', '.join(f.replace('_', ' ').title() for f in company.typical_role_families[:3])}",
    ]

    return OpportunityRecommendation(
        company=company.company,
        role_family=family,
        fit_score=fit,
        why_fit=why[:4],
        recommended_resume=resume_label,
        hiring_signals=hiring_signals,
        strengths=strengths,
        risks=risks,
    )


def rank_company_opportunities(profile: CandidateProfile) -> list[OpportunityRecommendation]:
    ranked = [score_company_opportunity(profile, cp) for cp in COMPANY_PROFILES.values()]
    return sorted(ranked, key=lambda r: (-r.fit_score, r.company))
