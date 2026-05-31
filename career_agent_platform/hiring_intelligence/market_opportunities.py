"""Market opportunity and dashboard intelligence builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from career_intelligence_engine.models.ontology import RoleFamilyId
from hiring_intelligence.industry_clusters import cluster_for_industries
from hiring_intelligence.opportunity_ranker import OpportunityRecommendation, rank_company_opportunities
from resume_routing.variants import RESUME_VARIANTS


@dataclass
class SkillHeatmapRow:
    skill: str
    market_demand: str
    candidate_strength: str
    recommendation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "Skill": self.skill,
            "Market Demand": self.market_demand,
            "Your Strength": self.candidate_strength,
            "Action": self.recommendation,
        }


_SKILL_MARKET_TABLE: tuple[tuple[str, str, str, str], ...] = (
    ("Release Governance", "Medium", "governance_experience", "Leverage"),
    ("RAG / GenAI Programs", "High", "transformation_focus", "Improve"),
    ("LLM Evaluation", "Very High", "ai_maturity", "Learn"),
    ("Enterprise TPM", "High", "primary_track_tpm", "Leverage"),
    ("AI Transformation Office", "High", "transformation_focus", "Leverage"),
    ("Cloud Migration", "Medium", "delivery_orientation", "Improve"),
    ("Stakeholder Governance", "Medium", "stakeholder_complexity", "Leverage"),
    ("Architecture Coordination", "Medium", "execution_orientation", "Improve"),
)


def _strength_label(profile: CandidateProfile, signal: str) -> str:
    if signal == "governance_experience":
        v = profile.governance_experience
    elif signal == "transformation_focus":
        v = profile.transformation_focus
    elif signal == "delivery_orientation":
        v = profile.delivery_orientation
    elif signal == "stakeholder_complexity":
        v = profile.stakeholder_complexity
    elif signal == "execution_orientation":
        v = profile.execution_orientation
    elif signal == "ai_maturity":
        ai = (profile.ai_maturity.value if profile.ai_maturity else "none").lower()
        mapping = {
            "none": 0.1,
            "awareness": 0.25,
            "pilot": 0.45,
            "practitioner": 0.65,
            "transformation_lead": 0.85,
        }
        v = mapping.get(ai, 0.2)
    elif signal == "primary_track_tpm":
        v = 0.75 if profile.primary_career_track.value == "technical_program_management" else 0.35
    else:
        v = 0.4
    if v >= 0.7:
        return "Strong"
    if v >= 0.45:
        return "Medium"
    return "Weak"


@dataclass
class MarketIntelligenceSnapshot:
    best_fit_companies: list[OpportunityRecommendation] = field(default_factory=list)
    best_fit_industries: list[tuple[str, float]] = field(default_factory=list)
    highest_confidence_role_families: list[tuple[str, float]] = field(default_factory=list)
    strategic_recommendations: list[str] = field(default_factory=list)
    resume_variant_performance: list[tuple[str, float]] = field(default_factory=list)
    skill_heatmap: list[SkillHeatmapRow] = field(default_factory=list)
    ai_readiness: str = ""
    executive_readiness: str = ""
    fastest_growing_gaps: list[str] = field(default_factory=list)
    most_requested_skills: list[str] = field(default_factory=list)
    recommended_upskilling: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_fit_companies": [c.to_dict() for c in self.best_fit_companies],
            "best_fit_industries": self.best_fit_industries,
            "highest_confidence_role_families": self.highest_confidence_role_families,
            "strategic_recommendations": self.strategic_recommendations,
            "resume_variant_performance": self.resume_variant_performance,
            "skill_heatmap": [r.to_dict() for r in self.skill_heatmap],
            "ai_readiness": self.ai_readiness,
            "executive_readiness": self.executive_readiness,
            "fastest_growing_gaps": self.fastest_growing_gaps,
            "most_requested_skills": self.most_requested_skills,
            "recommended_upskilling": self.recommended_upskilling,
        }


def build_skill_heatmap(profile: CandidateProfile) -> list[SkillHeatmapRow]:
    rows: list[SkillHeatmapRow] = []
    for skill, demand, signal, action in _SKILL_MARKET_TABLE:
        strength = _strength_label(profile, signal)
        rec = action
        if strength == "Weak" and action == "Leverage":
            rec = "Learn"
        elif strength == "Strong" and action == "Improve":
            rec = "Leverage"
        rows.append(
            SkillHeatmapRow(
                skill=skill,
                market_demand=demand,
                candidate_strength=strength,
                recommendation=rec,
            ),
        )
    return rows


def build_market_snapshot(profile: CandidateProfile) -> MarketIntelligenceSnapshot:
    companies = rank_company_opportunities(profile)[:8]
    industry_scores: dict[str, list[float]] = {}
    for opp in companies:
        from hiring_intelligence.company_mapper import lookup_company

        cp = lookup_company(opp.company)
        if cp is None:
            continue
        cluster = cluster_for_industries(cp.industries)
        industry_scores.setdefault(cluster, []).append(opp.fit_score)
    best_industries = sorted(
        ((k, sum(v) / len(v)) for k, v in industry_scores.items()),
        key=lambda x: -x[1],
    )[:5]

    role_scores = profile.role_family_scores or {}
    if not role_scores:
        role_scores = {profile.primary_career_track.value: 0.8}
    top_families = sorted(role_scores.items(), key=lambda x: -float(x[1]))[:5]
    def _family_label(key: str) -> str:
        try:
            fid = RoleFamilyId(key)
            return ROLE_FAMILIES[fid].display_name
        except (ValueError, KeyError):
            return key.replace("_", " ").title()

    readable_families = [(_family_label(k), float(v)) for k, v in top_families]

    ai = (profile.ai_maturity.value if profile.ai_maturity else "none").replace("_", " ").title()
    exec_ready = "High" if profile.leadership_level.value in {"org_leader", "executive"} else (
        "Medium" if profile.leadership_level.value in {"people_manager", "team_lead"} else "Developing"
    )

    gaps = profile.explanations.get("gap_analysis_primary", {}).get("gaps", [])
    if isinstance(gaps, list):
        gap_labels = [str(g) for g in gaps[:5]]
    else:
        gap_labels = ["LLM evaluation depth", "Hands-on AI engineering depth"]

    strategic: list[str] = []
    primary_display = ROLE_FAMILIES[profile.primary_career_track].display_name
    strategic.append(f"Your strongest market alignment is {primary_display.lower()}.")
    if best_industries:
        strategic.append(
            f"{best_industries[0][0]} companies show the highest deterministic fit for your profile.",
        )
    if profile.transformation_focus >= 0.5:
        strategic.append("Enterprise AI transformation employers are a credible target segment.")
    else:
        strategic.append(
            "AI Engineering roles remain stretch opportunities without stronger coding and AI depth.",
        )
    strategic.append("Release Governance and TPM remain your highest-confidence application tracks.")

    upskilling = [r.skill for r in build_skill_heatmap(profile) if r.recommendation == "Learn"][:4]
    requested = [r.skill for r in build_skill_heatmap(profile) if r.market_demand in {"High", "Very High"}][:5]

    variant_perf: list[tuple[str, float]] = []
    for variant in RESUME_VARIANTS.values():
        family = variant.suitable_role_families[0] if variant.suitable_role_families else ""
        score = float(role_scores.get(family, 0.0)) if role_scores else 0.5
        variant_perf.append((variant.label, round(score * 100, 1)))
    variant_perf.sort(key=lambda x: -x[1])

    return MarketIntelligenceSnapshot(
        best_fit_companies=companies,
        best_fit_industries=[(k, round(v, 1)) for k, v in best_industries],
        highest_confidence_role_families=readable_families,
        strategic_recommendations=strategic,
        resume_variant_performance=variant_perf[:6],
        skill_heatmap=build_skill_heatmap(profile),
        ai_readiness=ai,
        executive_readiness=exec_ready,
        fastest_growing_gaps=gap_labels or ["LLM evaluation", "AI engineering depth"],
        most_requested_skills=requested,
        recommended_upskilling=upskilling or ["LLM Evaluation", "RAG program delivery"],
    )
