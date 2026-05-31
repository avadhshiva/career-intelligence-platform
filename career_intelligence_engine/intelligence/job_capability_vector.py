"""Normalized job capability vectors — same 15 dimensions as candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from career_intelligence_engine.intelligence.candidate_vector import (
    _TITLE_DIMENSION_HINTS,
    _score_dimension_calibrated,
)
from career_intelligence_engine.models.ontology import AIMaturity, RoleFamilyId
from career_intelligence_engine.ontology.capability_vectors import (
    CAPABILITY_DIMENSIONS,
    get_role_family_vector,
    normalize_vector,
)

_AI_MATURITY_BOOST: dict[AIMaturity, float] = {
    AIMaturity.ENTERPRISE_AI_OWNER: 0.85,
    AIMaturity.TRANSFORMATION_LEAD: 0.55,
    AIMaturity.PRACTITIONER: 0.38,
    AIMaturity.PILOT: 0.22,
    AIMaturity.AWARENESS: 0.12,
    AIMaturity.NONE: 0.0,
}


@dataclass
class JobVectorResult:
    vector: dict[str, float]
    raw_scores: dict[str, float] = field(default_factory=dict)
    evidence: dict[str, list[str]] = field(default_factory=dict)


def _title_boosts(title: str | None) -> dict[str, float]:
    boosts: dict[str, float] = {d: 0.0 for d in CAPABILITY_DIMENSIONS}
    if not title:
        return boosts
    titles_lower = title.lower()
    cap = 0.28
    for hint, dimensions in _TITLE_DIMENSION_HINTS.items():
        if hint in titles_lower:
            for dim in dimensions:
                boosts[dim] = min(1.0, boosts[dim] + cap)
    if " ai " in f" {titles_lower} " or titles_lower.startswith("ai "):
        boosts["ai_strategy"] = min(1.0, boosts["ai_strategy"] + 0.15)
    return boosts


def _scalar_boosts(hints: dict[str, Any]) -> dict[str, float]:
    boosts: dict[str, float] = {d: 0.0 for d in CAPABILITY_DIMENSIONS}
    boosts["enterprise_governance"] = max(
        boosts["enterprise_governance"],
        float(hints.get("governance_intensity", 0.0)) * 0.9,
    )
    boosts["product_thinking"] = max(
        boosts["product_thinking"],
        float(hints.get("product_ownership_required", 0.0)) * 0.95,
    )
    boosts["operational_management"] = max(
        boosts["operational_management"],
        float(hints.get("operational_ownership_required", 0.0)) * 0.95,
    )
    boosts["architecture_coordination"] = max(
        boosts["architecture_coordination"],
        float(hints.get("architecture_depth", 0.0)) * 0.9,
    )
    boosts["transformation_strategy"] = max(
        boosts["transformation_strategy"],
        float(hints.get("transformation_focus", 0.0)) * 0.75,
    )
    ai = hints.get("ai_maturity")
    if isinstance(ai, AIMaturity):
        boosts["ai_strategy"] = max(boosts["ai_strategy"], _AI_MATURITY_BOOST.get(ai, 0.0))
    return boosts


def _family_baseline(primary: RoleFamilyId | None) -> dict[str, float]:
    if primary is None:
        return {d: 0.0 for d in CAPABILITY_DIMENSIONS}
    family_vec = get_role_family_vector(primary)
    return {d: family_vec.get(d, 0.0) * 0.35 for d in CAPABILITY_DIMENSIONS}


def extract_job_vector(
    *,
    corpus: str,
    title: str | None = None,
    bullets: list[str] | None = None,
    job_hints: dict[str, Any] | None = None,
) -> JobVectorResult:
    """
    Build L2-normalized job capability vector using the same dimension basis as candidates.
    """
    hints = job_hints or {}
    full_corpus = corpus
    if bullets:
        full_corpus = f"{corpus}\n" + "\n".join(bullets)

    raw_scores: dict[str, float] = {d: 0.0 for d in CAPABILITY_DIMENSIONS}
    evidence: dict[str, list[str]] = {}

    for dim in CAPABILITY_DIMENSIONS:
        score, dim_evidence = _score_dimension_calibrated(
            full_corpus, dim, ownership_strength=0.5
        )
        raw_scores[dim] = score
        if dim_evidence:
            evidence[dim] = dim_evidence

    title_boosts = _title_boosts(title)
    scalar_boosts = _scalar_boosts(hints)
    primary = hints.get("primary_role_family")
    baseline = _family_baseline(primary if isinstance(primary, RoleFamilyId) else None)

    for dim in CAPABILITY_DIMENSIONS:
        raw_scores[dim] = round(
            max(
                raw_scores[dim],
                title_boosts[dim],
                scalar_boosts[dim],
                baseline[dim],
            ),
            3,
        )

    if hints.get("product_ownership_required", 0) >= 0.65:
        raw_scores["product_thinking"] = max(raw_scores["product_thinking"], 0.55)
        evidence.setdefault("gates", []).append("product_ownership_required")
    if hints.get("operational_ownership_required", 0) >= 0.65:
        raw_scores["operational_management"] = max(raw_scores["operational_management"], 0.55)
        evidence.setdefault("gates", []).append("operational_ownership_required")
    if hints.get("architecture_depth", 0) >= 0.65:
        raw_scores["architecture_coordination"] = max(
            raw_scores["architecture_coordination"], 0.50
        )
        evidence.setdefault("gates", []).append("architecture_depth_required")

    normalized = normalize_vector(
        {d: raw_scores.get(d, 0.0) for d in CAPABILITY_DIMENSIONS}
    )
    return JobVectorResult(
        vector=normalized,
        raw_scores=raw_scores,
        evidence=evidence,
    )
