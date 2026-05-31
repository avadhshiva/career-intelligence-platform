"""Deterministic evidence depth, frequency thresholds, and AI maturity calibration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from career_intelligence_engine.intelligence.capability_density import (
    score_capability_density,
)
from career_intelligence_engine.models.ontology import AIMaturity, ParsedResume

# Ownership verb tiers (stronger verbs → higher weight)
OWNERSHIP_VERB_WEIGHT: dict[str, float] = {
    "owned": 3.0,
    "directed": 2.8,
    "governed": 2.8,
    "led": 2.5,
    "spearheaded": 2.5,
    "orchestrated": 2.4,
    "drove": 2.2,
    "managed": 2.0,
    "established": 1.9,
    "championed": 1.6,
    "facilitated": 1.3,
    "coordinated": 1.2,
    "supported": 0.6,
    "participated": 0.4,
    "assisted": 0.35,
    "contributed": 0.5,
}

_OWNERSHIP_RE = re.compile(
    r"\b(" + "|".join(re.escape(v) for v in OWNERSHIP_VERB_WEIGHT) + r")\b",
    re.I,
)

# Scale / accountability signals
_SCALE_PATTERNS = [
    re.compile(r"\b(fortune 500|global matrix|multi-region|enterprise-wide)\b", re.I),
    re.compile(r"\b(\$\d+[mb]|\d+\+?\s*(workstreams|teams|engineers|countries))\b", re.I),
    re.compile(r"\b(p&l|budget ownership|portfolio budget|program budget)\b", re.I),
    re.compile(r"\b(production|in production|production deployment|sla|uptime)\b", re.I),
]

# AI signal buckets (separate exposure vs leadership vs governance)
_AI_EXPOSURE = re.compile(
    r"\b(genai|generative ai|machine learning|llm|copilot|ai initiative)\b",
    re.I,
)
_AI_STRATEGY = re.compile(
    r"\b(ai strategy|ai roadmap|ai transformation|enterprise ai)\b",
    re.I,
)
_AI_GOVERNANCE = re.compile(
    r"\b(ai governance|model governance|responsible ai|ai policy|ai risk|"
    r"ai compliance|ai ethics|model risk)\b",
    re.I,
)
_AI_OPERATIONAL = re.compile(
    r"\b(mlops|ai platform|production ai|ai coe|ai center of excellence|"
    r"owned ai|ai program delivery)\b",
    re.I,
)
_GENERIC_TRANSFORM = re.compile(
    r"\b(digital transformation|transformation|modernization|operating model)\b",
    re.I,
)

_STRONG_OWNERSHIP = frozenset(
    {"owned", "directed", "governed", "led", "spearheaded", "orchestrated"}
)


@dataclass
class EvidenceDepthResult:
    """Depth-weighted evidence summary for calibration."""

    ownership_strength: float = 0.0
    scale_score: float = 0.0
    governance_cadence: float = 0.0
    operational_accountability: float = 0.0
    ai_exposure_hits: int = 0
    ai_strategy_hits: int = 0
    ai_governance_hits: int = 0
    ai_operational_hits: int = 0
    transform_generic_hits: int = 0
    org_transform_hits: int = 0
    strong_ownership_hits: int = 0
    auxiliary_scores: dict[str, float] = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)


def frequency_to_score(hit_count: int, *, strong: bool = False) -> float:
    """
    Map mention frequency to a bounded score.

    1 mention = weak; 2 = light; 3+ = moderate/strong (capped).
    """
    if hit_count <= 0:
        return 0.0
    if hit_count == 1:
        return 0.10 if not strong else 0.14
    if hit_count == 2:
        return 0.22 if not strong else 0.28
    return round(min(0.85, 0.30 + hit_count * 0.10), 3)


def score_ownership_in_corpus(corpus: str) -> tuple[float, int]:
    """Aggregate ownership verb strength across corpus."""
    total = 0.0
    strong = 0
    for match in _OWNERSHIP_RE.finditer(corpus):
        verb = match.group(1).lower()
        w = OWNERSHIP_VERB_WEIGHT.get(verb, 1.0)
        total += w
        if verb in _STRONG_OWNERSHIP:
            strong += 1
    if total <= 0:
        return 0.0, 0
    return round(min(1.0, total * 0.06), 3), strong


def analyze_evidence_depth(parsed: ParsedResume) -> EvidenceDepthResult:
    """Compute depth-weighted evidence from resume text and bullets."""
    bullets = parsed.bullets or []
    corpus = "\n".join([parsed.raw_text] + bullets + parsed.job_titles).lower()
    bullet_corpus = "\n".join(bullets).lower()

    density = score_capability_density(parsed.raw_text, bullets)

    ownership_strength, strong_hits = score_ownership_in_corpus(bullet_corpus or corpus)
    ownership_strength = round(
        min(1.0, ownership_strength + density.ownership_score * 0.08),
        3,
    )

    scale_hits = sum(len(p.findall(corpus)) for p in _SCALE_PATTERNS)
    scale_score = frequency_to_score(scale_hits, strong=True)

    gov_cadence = min(
        1.0,
        density.enterprise_scope_score * 0.12
        + frequency_to_score(
            len(
                re.findall(
                    r"\b(steering committee|governance board|executive sponsor|qbr)\b",
                    corpus,
                    re.I,
                )
            ),
            strong=True,
        ),
    )

    prod_hits = len(
        re.findall(
            r"\b(production|in production|operational|run the|sla|incident)\b",
            corpus,
            re.I,
        )
    )
    operational = round(
        min(1.0, frequency_to_score(prod_hits) + ownership_strength * 0.15),
        3,
    )

    ai_exp = len(_AI_EXPOSURE.findall(corpus))
    ai_strat = len(_AI_STRATEGY.findall(corpus))
    ai_gov = len(_AI_GOVERNANCE.findall(corpus))
    ai_ops = len(_AI_OPERATIONAL.findall(corpus))
    transform_gen = len(_GENERIC_TRANSFORM.findall(corpus))
    org_transform = len(
        re.findall(
            r"\b(operating model|organizational transformation|target operating model|"
            r"business transformation)\b",
            corpus,
            re.I,
        )
    )

    aux = {
        "ai_exposure": frequency_to_score(ai_exp),
        "ai_strategy_depth": frequency_to_score(ai_strat, strong=ai_strat >= 3),
        "ai_governance_depth": frequency_to_score(ai_gov, strong=ai_gov >= 2),
        "ai_operational_ownership": frequency_to_score(ai_ops, strong=True),
        "ai_program_delivery": round(
            min(
                1.0,
                frequency_to_score(ai_ops) * 0.5
                + frequency_to_score(ai_strat) * 0.3
                + ownership_strength * 0.2,
            ),
            3,
        ),
    }

    signals: list[str] = []
    if ai_exp == 1:
        signals.append("ai_exposure_single_mention")
    if ai_strat >= 3:
        signals.append("ai_strategy_repeated")
    if ai_gov >= 2:
        signals.append("ai_governance_repeated")
    if strong_hits >= 2:
        signals.append("strong_ownership_verbs")

    return EvidenceDepthResult(
        ownership_strength=ownership_strength,
        scale_score=scale_score,
        governance_cadence=round(gov_cadence, 3),
        operational_accountability=operational,
        ai_exposure_hits=ai_exp,
        ai_strategy_hits=ai_strat,
        ai_governance_hits=ai_gov,
        ai_operational_hits=ai_ops,
        transform_generic_hits=transform_gen,
        org_transform_hits=org_transform,
        strong_ownership_hits=strong_hits,
        auxiliary_scores=aux,
        signals=signals,
    )


def infer_ai_maturity(depth: EvidenceDepthResult) -> AIMaturity:
    """
    Evidence-based AI maturity tiers.

    awareness → pilot → practitioner → transformation_lead → enterprise_ai_owner
    """
    gov = depth.ai_governance_hits
    strat = depth.ai_strategy_hits
    ops = depth.ai_operational_hits
    exp = depth.ai_exposure_hits
    own = depth.ownership_strength
    strong = depth.strong_ownership_hits

    # Enterprise AI owner: governance + strategy + operational ownership + cadence
    if (
        gov >= 2
        and strat >= 2
        and ops >= 1
        and own >= 0.45
        and depth.governance_cadence >= 0.25
    ):
        return AIMaturity.ENTERPRISE_AI_OWNER

    # Transformation lead: repeated strategy + org transformation + strong ownership
    if strat >= 3 and own >= 0.35 and depth.transform_generic_hits >= 2:
        return AIMaturity.TRANSFORMATION_LEAD

    if strat >= 2 and ops >= 1 and own >= 0.30:
        return AIMaturity.TRANSFORMATION_LEAD

    # Practitioner: delivery/execution level AI program work
    if ops >= 2 or (ops >= 1 and strat >= 1 and own >= 0.25):
        return AIMaturity.PRACTITIONER

    if strat >= 2 and exp >= 1:
        return AIMaturity.PRACTITIONER

    # Pilot: limited initiative exposure
    if exp >= 2 or (exp >= 1 and ops >= 1):
        return AIMaturity.PILOT

    if strat == 1 or exp == 1:
        return AIMaturity.AWARENESS

    if exp > 0 or strat > 0:
        return AIMaturity.AWARENESS

    return AIMaturity.NONE


def calibrated_transformation_focus(depth: EvidenceDepthResult) -> float:
    """Transformation focus with reduced generic-keyword inflation."""
    generic = frequency_to_score(depth.transform_generic_hits)
    if depth.transform_generic_hits <= 1:
        generic *= 0.5
    org = frequency_to_score(depth.org_transform_hits, strong=depth.org_transform_hits >= 2)
    strat = depth.auxiliary_scores.get("ai_strategy_depth", 0.0)
    if depth.ai_strategy_hits < 3:
        strat *= 0.55

    score = (
        generic * 0.35
        + org * 0.25
        + strat * 0.20
        + depth.ownership_strength * 0.20
    )
    return round(min(1.0, score), 2)


def calibrated_dimension_score(
    hit_count: int,
    *,
    ownership_multiplier: float = 1.0,
    require_ownership: bool = False,
    ownership_strength: float = 0.0,
) -> float:
    """Frequency-thresholded dimension score with optional ownership gate."""
    base = frequency_to_score(hit_count, strong=hit_count >= 3)
    if hit_count == 1:
        base *= 0.65
    if require_ownership and ownership_strength < 0.2:
        base *= 0.45
    return round(min(1.0, base * ownership_multiplier), 3)
