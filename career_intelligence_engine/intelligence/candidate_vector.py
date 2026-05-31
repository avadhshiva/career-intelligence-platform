"""Infer normalized candidate capability vectors from resume evidence (calibrated)."""



from __future__ import annotations



import re

from dataclasses import dataclass, field



from career_intelligence_engine.intelligence.evidence_calibration import (

    EvidenceDepthResult,

    analyze_evidence_depth,

    calibrated_dimension_score,

    frequency_to_score,

)

from career_intelligence_engine.models.candidate_profile import CandidateProfile

from career_intelligence_engine.models.ontology import (

    AIMaturity,

    EnterpriseExposure,

    LeadershipLevel,

    ParsedResume,

)

from career_intelligence_engine.ontology.capability_vectors import (

    CAPABILITY_DIMENSIONS,

    normalize_vector,

)



# Dimension signal patterns (deterministic keyword / regex evidence)

_DIMENSION_SIGNALS: dict[str, list[re.Pattern[str]]] = {

    "enterprise_governance": [

        re.compile(

            r"\b(governance board|steering committee|portfolio governance|"

            r"program governance|benefits realization)\b",

            re.I,

        ),

        re.compile(r"\b(investment committee|funding governance|enterprise pmo)\b", re.I),

    ],

    "technical_execution": [

        re.compile(r"\b(sdlc|ci/?cd|dependency management|engineering coordination|release train)\b", re.I),

        re.compile(r"\b(cross-functional technical|mlops|devops|platform engineering)\b", re.I),

    ],

    "transformation_strategy": [

        re.compile(r"\b(operating model redesign|organizational transformation|target operating model)\b", re.I),

        re.compile(r"\b(enterprise transformation|business transformation|org redesign)\b", re.I),

    ],

    "ai_strategy": [

        re.compile(r"\b(ai strategy|ai roadmap|enterprise ai strategy)\b", re.I),

        re.compile(r"\b(ai transformation program|genai strategy)\b", re.I),

    ],

    "delivery_execution": [

        re.compile(r"\b(client delivery|rollout|implementation|multi-region|fortune 500)\b", re.I),

        re.compile(r"\b(program delivery|milestone delivery|go-live|cutover)\b", re.I),

    ],

    "stakeholder_complexity": [

        re.compile(r"\b(stakeholder management|executive stakeholder|global matrix|cross-bu)\b", re.I),

        re.compile(r"\b(multi-geography|enterprise-wide|cross-functional)\b", re.I),

    ],

    "organizational_leadership": [

        re.compile(r"\b(people manager|org leader|team building|direct reports|headcount)\b", re.I),

        re.compile(r"\b(organizational leadership|people leadership)\b", re.I),

    ],

    "operational_management": [

        re.compile(r"\b(run operations|operational continuity|sla management|incident management)\b", re.I),

        re.compile(r"\b(service operations|it operations|noc|production support)\b", re.I),

    ],

    "product_thinking": [

        re.compile(r"\b(product roadmap|product owner|backlog|customer discovery|product strategy)\b", re.I),

        re.compile(r"\b(user stories|product vision|go-to-market|gtm)\b", re.I),

    ],

    "engineering_depth": [

        re.compile(r"\b(software engineer|coding|code review|full stack|backend|frontend)\b", re.I),

        re.compile(r"\b(developer|programming|java|python|\.net|kubernetes)\b", re.I),

    ],

    "release_governance": [

        re.compile(r"\b(release governance|release train|safe\b|pi planning|release management)\b", re.I),

        re.compile(r"\b(sdlc governance|release calendar|deployment governance)\b", re.I),

    ],

    "architecture_coordination": [

        re.compile(r"\b(architecture review|solution architecture|enterprise architecture)\b", re.I),

        re.compile(r"\b(architecture board|technical architecture|design authority)\b", re.I),

    ],

    "portfolio_management": [

        re.compile(r"\b(portfolio management|program portfolio|strategic portfolio)\b", re.I),

        re.compile(r"\b(prioritization framework|portfolio prioritization|investment portfolio)\b", re.I),

    ],

    "executive_communication": [

        re.compile(r"\b(c-suite|executive sponsor|board of directors|executive reporting)\b", re.I),

        re.compile(r"\b(qbr|quarterly business review|executive committee)\b", re.I),

    ],

    "change_management": [

        re.compile(r"\b(change management|adoption|organizational change|change enablement)\b", re.I),

        re.compile(r"\b(training rollout|change champion|ocm)\b", re.I),

    ],

}



# Dimensions that require ownership verbs for full credit

_OWNERSHIP_GATED = frozenset(

    {

        "ai_strategy",

        "transformation_strategy",

        "portfolio_management",

        "enterprise_governance",

    }

)



_TITLE_DIMENSION_HINTS: dict[str, list[str]] = {

    "technical program": ["technical_execution", "release_governance", "architecture_coordination"],

    "program manager": ["portfolio_management", "delivery_execution", "stakeholder_complexity"],

    "program director": ["portfolio_management", "executive_communication", "organizational_leadership"],

    "product manager": ["product_thinking", "stakeholder_complexity"],

    "product owner": ["product_thinking", "delivery_execution"],

    "operations manager": ["operational_management", "delivery_execution"],

    "transformation lead": ["transformation_strategy", "change_management"],

    "chief": ["executive_communication", "organizational_leadership"],

    "director": ["organizational_leadership", "executive_communication"],

    "vp ": ["executive_communication", "organizational_leadership"],

}



# Weak title hint for AI exposure only (not full strategy leadership)

_AI_TITLE_HINT = ["ai_strategy"]





@dataclass

class CandidateVectorResult:

    vector: dict[str, float]

    raw_scores: dict[str, float] = field(default_factory=dict)

    evidence: dict[str, list[str]] = field(default_factory=dict)





def _score_dimension_calibrated(

    corpus: str,

    dimension: str,

    *,

    ownership_strength: float,

) -> tuple[float, list[str]]:

    patterns = _DIMENSION_SIGNALS.get(dimension, [])

    hits = 0

    evidence: list[str] = []

    for pattern in patterns:

        matches = pattern.findall(corpus)

        if matches:

            hits += len(matches)

            evidence.append(f"{dimension}:{pattern.pattern[:40]}")



    gated = dimension in _OWNERSHIP_GATED

    score = calibrated_dimension_score(

        hits,

        ownership_multiplier=1.0 + min(0.25, ownership_strength * 0.3),

        require_ownership=gated,

        ownership_strength=ownership_strength,

    )

    return score, evidence[:3]





def _title_boosts(titles: list[str], *, ownership_strength: float) -> dict[str, float]:

    boosts: dict[str, float] = {d: 0.0 for d in CAPABILITY_DIMENSIONS}

    titles_lower = " ".join(titles).lower()

    title_cap = 0.22 + min(0.18, ownership_strength * 0.2)



    for hint, dimensions in _TITLE_DIMENSION_HINTS.items():

        if hint in titles_lower:

            for dim in dimensions:

                boosts[dim] = min(1.0, boosts[dim] + title_cap)



    if " ai " in f" {titles_lower} " or titles_lower.startswith("ai "):

        for dim in _AI_TITLE_HINT:

            boosts[dim] = min(1.0, boosts[dim] + 0.10)



    return boosts





def _apply_depth_adjustments(

    raw_scores: dict[str, float],

    depth: EvidenceDepthResult,

) -> dict[str, float]:

    """Boost dimensions with depth evidence; dampen AI inflation."""

    out = dict(raw_scores)



    out["technical_execution"] = max(

        out["technical_execution"],

        depth.operational_accountability * 0.35,

    )

    out["delivery_execution"] = max(

        out["delivery_execution"],

        depth.scale_score * 0.4,

    )

    out["enterprise_governance"] = max(

        out["enterprise_governance"],

        depth.governance_cadence * 0.85,

    )

    out["stakeholder_complexity"] = max(

        out["stakeholder_complexity"],

        depth.scale_score * 0.35,

    )



    # AI strategy: exposure vs leadership

    ai_strat = depth.auxiliary_scores.get("ai_strategy_depth", 0.0)

    if depth.ai_strategy_hits < 3:

        ai_strat = min(ai_strat, 0.28)

    if depth.ai_exposure_hits >= 1 and depth.ai_strategy_hits < 2:

        ai_strat = min(ai_strat, 0.18)

    out["ai_strategy"] = max(out["ai_strategy"], ai_strat)



    # Generic transformation language — cap unless org-level evidence

    if depth.transform_generic_hits >= 2 and depth.org_transform_hits >= 1:

        out["transformation_strategy"] = max(

            out["transformation_strategy"],

            frequency_to_score(depth.org_transform_hits, strong=True) * 0.7,

        )

    elif depth.org_transform_hits >= 1:

        out["transformation_strategy"] = max(

            out["transformation_strategy"],

            frequency_to_score(depth.org_transform_hits) * 0.5,

        )

    else:

        out["transformation_strategy"] = min(

            out["transformation_strategy"],

            frequency_to_score(depth.transform_generic_hits) * 0.45,

        )



    # Auxiliary scores for role-family penalty gates

    out["ai_governance_depth"] = depth.auxiliary_scores.get("ai_governance_depth", 0.0)

    out["ai_program_delivery"] = depth.auxiliary_scores.get("ai_program_delivery", 0.0)

    out["ai_exposure"] = depth.auxiliary_scores.get("ai_exposure", 0.0)



    return {k: round(min(1.0, v), 3) for k, v in out.items()}





def _profile_scalar_boosts(profile: CandidateProfile) -> dict[str, float]:

    """Map profile scalars into capability dimensions (conservative AI boosts)."""

    boosts: dict[str, float] = {d: 0.0 for d in CAPABILITY_DIMENSIONS}



    boosts["enterprise_governance"] = max(

        boosts["enterprise_governance"],

        profile.governance_experience * 0.85,

    )

    boosts["stakeholder_complexity"] = max(

        boosts["stakeholder_complexity"],

        profile.stakeholder_complexity * 0.85,

    )

    boosts["delivery_execution"] = max(

        boosts["delivery_execution"],

        profile.delivery_orientation * 0.8,

    )

    boosts["transformation_strategy"] = max(

        boosts["transformation_strategy"],

        profile.transformation_focus * 0.55,

    )

    boosts["technical_execution"] = max(

        boosts["technical_execution"],

        profile.execution_orientation * 0.75,

    )

    boosts["executive_communication"] = max(

        boosts["executive_communication"],

        profile.strategic_orientation * 0.5,

    )



    if profile.leadership_level in (

        LeadershipLevel.ORG_LEADER,

        LeadershipLevel.EXECUTIVE,

    ):

        boosts["organizational_leadership"] = max(boosts["organizational_leadership"], 0.65)

        boosts["executive_communication"] = max(boosts["executive_communication"], 0.6)

    elif profile.leadership_level == LeadershipLevel.PEOPLE_MANAGER:

        boosts["organizational_leadership"] = max(boosts["organizational_leadership"], 0.4)



    enterprise_map = {

        EnterpriseExposure.DEEP: 0.7,

        EnterpriseExposure.STRONG: 0.55,

        EnterpriseExposure.MODERATE: 0.35,

        EnterpriseExposure.LIMITED: 0.18,

    }

    ent_boost = enterprise_map.get(profile.enterprise_experience, 0.0)

    boosts["enterprise_governance"] = max(boosts["enterprise_governance"], ent_boost)

    boosts["stakeholder_complexity"] = max(boosts["stakeholder_complexity"], ent_boost * 0.75)



    ai_map = {

        AIMaturity.ENTERPRISE_AI_OWNER: 0.85,

        AIMaturity.TRANSFORMATION_LEAD: 0.55,

        AIMaturity.PRACTITIONER: 0.38,

        AIMaturity.PILOT: 0.22,

        AIMaturity.AWARENESS: 0.12,

    }

    ai_boost = ai_map.get(profile.ai_maturity, 0.0)

    boosts["ai_strategy"] = max(boosts["ai_strategy"], ai_boost)



    return boosts





def extract_candidate_vector(

    profile: CandidateProfile,

    parsed: ParsedResume | None = None,

) -> CandidateVectorResult:

    """

    Build a normalized capability vector for a candidate.



    Uses resume text when available; falls back to profile scalars and skills.

    """

    if profile.capability_vector and profile.capability_raw_scores:

        raw = dict(profile.capability_raw_scores)

        raw.setdefault("ai_governance_depth", 0.0)

        raw.setdefault("ai_program_delivery", 0.0)

        raw.setdefault("ai_exposure", 0.0)

        return CandidateVectorResult(

            vector=dict(profile.capability_vector),

            raw_scores=raw,

            evidence={"source": ["stored_profile_vector"]},

        )



    corpus_parts: list[str] = []

    titles: list[str] = []

    depth: EvidenceDepthResult | None = None



    if parsed is not None:

        corpus_parts.extend([parsed.raw_text, "\n".join(parsed.bullets)])

        titles = list(parsed.job_titles)

        depth = analyze_evidence_depth(parsed)

    else:

        exec_signals = profile.explanations.get("executive", [])

        if isinstance(exec_signals, list):

            corpus_parts.extend(exec_signals)



    corpus_parts.append(" ".join(profile.top_skills))

    corpus = "\n".join(corpus_parts).lower()

    ownership_strength = depth.ownership_strength if depth else 0.0



    raw_scores: dict[str, float] = {d: 0.0 for d in CAPABILITY_DIMENSIONS}

    evidence: dict[str, list[str]] = {}



    for dim in CAPABILITY_DIMENSIONS:

        text_score, dim_evidence = _score_dimension_calibrated(

            corpus, dim, ownership_strength=ownership_strength

        )

        raw_scores[dim] = text_score

        if dim_evidence:

            evidence[dim] = dim_evidence



    title_boosts = _title_boosts(titles, ownership_strength=ownership_strength)

    scalar_boosts = _profile_scalar_boosts(profile)



    for dim in CAPABILITY_DIMENSIONS:

        raw_scores[dim] = round(

            max(raw_scores[dim], title_boosts[dim], scalar_boosts[dim]),

            3,

        )



    if depth is not None:

        raw_scores = _apply_depth_adjustments(raw_scores, depth)

        evidence["calibration"] = depth.signals

    if parsed is not None:

        from career_intelligence_engine.ontology.role_family_calibration import (
            build_calibration_context,
        )

        cal = build_calibration_context(parsed)
        raw_scores["product_ownership_depth"] = cal.product_ownership_depth
        raw_scores["operational_run_depth"] = cal.operational_run_depth
        raw_scores["product_thinking"] = min(
            raw_scores.get("product_thinking", 0.0),
            max(cal.product_ownership_depth, cal.raw_scores.get("product_thinking", 0.0)),
        )
        if cal.operational_run_depth < 0.08:
            raw_scores["operational_management"] = min(
                raw_scores.get("operational_management", 0.0),
                0.05,
            )
        else:
            raw_scores["operational_management"] = max(
                raw_scores.get("operational_management", 0.0),
                cal.operational_run_depth,
            )
        evidence["role_family_calibration"] = cal.signals
        for dim in CAPABILITY_DIMENSIONS:
            if dim in cal.raw_scores:
                raw_scores[dim] = max(raw_scores.get(dim, 0.0), cal.raw_scores[dim])
        if cal.separation_v2 is not None:
            evidence["separation_v2"] = cal.separation_v2.signals



    normalized = normalize_vector(

        {d: raw_scores.get(d, 0.0) for d in CAPABILITY_DIMENSIONS}

    )

    return CandidateVectorResult(

        vector=normalized,

        raw_scores=raw_scores,

        evidence=evidence,

    )


