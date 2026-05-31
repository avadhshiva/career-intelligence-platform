"""Vector-based role-family proximity — cosine similarity with differentiation penalties."""

from __future__ import annotations

from dataclasses import dataclass, field

from career_intelligence_engine.intelligence.candidate_vector import (
    CandidateVectorResult,
    extract_candidate_vector,
)
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.capability_vectors import (
    cosine_similarity,
    dimension_contributions,
    get_role_family_vector,
    label_dimension,
)
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from career_intelligence_engine.ontology.role_family_calibration import (
    apply_vector_negative_constraints,
    calibration_context_from_raw,
)
from career_intelligence_engine.ontology.role_family_separation_v2 import (
    apply_separation_v2_proximity,
    recruiter_readable_explanation,
)

# Evidence gates: without minimum raw evidence, apply proximity penalty
_DIFFERENTIATION_RULES: dict[RoleFamilyId, dict] = {
    RoleFamilyId.OPERATIONS: {
        "required": ["operational_management"],
        "min_raw": 0.15,
        "penalty": 0.40,
        "missing_label": "Operational Continuity",
    },
    RoleFamilyId.ENTERPRISE_OPERATIONS: {
        "required": ["operational_management"],
        "min_raw": 0.18,
        "penalty": 0.38,
        "missing_label": "Operational Continuity",
    },
    RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT: {
        "required": ["technical_execution", "architecture_coordination"],
        "min_raw": 0.18,
        "penalty": 0.32,
        "missing_label": "Engineering Coordination",
    },
    RoleFamilyId.AI_TRANSFORMATION: {
        "required": ["ai_strategy", "transformation_strategy"],
        "min_raw": 0.28,
        "penalty": 0.34,
        "missing_label": "Operating-Model Transformation",
        "auxiliary": {},
    },
    RoleFamilyId.AI_GOVERNANCE: {
        "required": ["enterprise_governance", "ai_strategy"],
        "min_raw": 0.24,
        "penalty": 0.45,
        "missing_label": "Enterprise AI Governance",
        "auxiliary": {"ai_governance_depth": 0.22},
    },
    RoleFamilyId.AI_PROGRAM_MANAGEMENT: {
        "required": ["technical_execution", "delivery_execution"],
        "min_raw": 0.20,
        "penalty": 0.38,
        "missing_label": "AI Program Delivery Ownership",
        "auxiliary": {"ai_program_delivery": 0.25},
    },
    RoleFamilyId.PROGRAM_LEADERSHIP: {
        "required": ["portfolio_management", "stakeholder_complexity"],
        "min_raw": 0.22,
        "penalty": 0.22,
        "missing_label": "Portfolio Leadership",
    },
    RoleFamilyId.ENTERPRISE_DELIVERY: {
        "required": ["delivery_execution"],
        "min_raw": 0.25,
        "penalty": 0.20,
        "missing_label": "Enterprise Delivery Ownership",
    },
    RoleFamilyId.TRANSFORMATION_OFFICE: {
        "required": ["transformation_strategy", "change_management"],
        "min_raw": 0.2,
        "penalty": 0.28,
        "missing_label": "Transformation Office Governance",
    },
    RoleFamilyId.PRODUCT_MANAGEMENT: {
        "required": ["product_thinking"],
        "min_raw": 0.22,
        "penalty": 0.40,
        "missing_label": "Product Ownership",
    },
    RoleFamilyId.PRODUCT_DELIVERY: {
        "required": ["product_thinking"],
        "min_raw": 0.20,
        "penalty": 0.38,
        "missing_label": "Product Roadmap Ownership",
    },
    RoleFamilyId.RELEASE_GOVERNANCE: {
        "required": ["release_governance"],
        "min_raw": 0.18,
        "penalty": 0.28,
        "missing_label": "Release Governance",
    },
    RoleFamilyId.SOFTWARE_ENGINEERING: {
        "required": ["engineering_depth"],
        "min_raw": 0.25,
        "penalty": 0.40,
        "missing_label": "Engineering Depth",
    },
}


@dataclass
class VectorProximityResult:
    proximity: float
    semantic_distance: float
    distance: float
    dominant_dimensions: list[str]
    weak_dimensions: list[str]
    missing_dimensions: list[str]
    explanation: str
    detail_explanations: list[str] = field(default_factory=list)
    penalty_applied: float = 0.0
    raw_cosine: float = 0.0


def _apply_differentiation_penalty(
    family_id: RoleFamilyId,
    raw_scores: dict[str, float],
    proximity: float,
) -> tuple[float, float, list[str]]:
    """Reduce proximity when required evidence dimensions are absent."""
    rule = _DIFFERENTIATION_RULES.get(family_id)
    if not rule:
        return proximity, 0.0, []

    required = rule["required"]
    min_raw = rule["min_raw"]
    penalty = rule["penalty"]
    missing: list[str] = []

    for dim in required:
        if raw_scores.get(dim, 0.0) < min_raw:
            missing.append(label_dimension(dim))

    for aux_key, aux_min in rule.get("auxiliary", {}).items():
        if raw_scores.get(aux_key, 0.0) < aux_min:
            label = aux_key.replace("_", " ").title()
            if label not in missing:
                missing.append(label)

    if not missing:
        return proximity, 0.0, []

    adjusted = round(max(0.0, proximity - penalty), 4)
    return adjusted, penalty, missing


def score_vector_proximity(
    candidate_vector: dict[str, float],
    family_id: RoleFamilyId,
    *,
    raw_scores: dict[str, float] | None = None,
    cal_ctx=None,
) -> VectorProximityResult:
    """Score proximity between candidate and role-family capability vectors."""
    role_vector = get_role_family_vector(family_id)
    raw_cosine = cosine_similarity(candidate_vector, role_vector)

    raw = raw_scores or {}
    proximity, penalty, missing = _apply_differentiation_penalty(
        family_id, raw, raw_cosine
    )

    if cal_ctx is None and raw:
        cal_ctx = calibration_context_from_raw(raw)

    neg_penalty = 0.0
    neg_explanation: str | None = None
    if cal_ctx is not None:
        proximity, neg_penalty, neg_explanation = apply_vector_negative_constraints(
            family_id, proximity, raw, cal_ctx
        )
        penalty = round(penalty + neg_penalty, 4)
        if neg_explanation and neg_penalty > 0:
            missing = list(missing)

    sep_penalty = 0.0
    sep_explanation: str | None = None
    if cal_ctx is not None and cal_ctx.separation_v2 is not None:
        proximity, sep_penalty, sep_explanation = apply_separation_v2_proximity(
            family_id,
            proximity,
            raw,
            cal_ctx.separation_v2,
        )
        penalty = round(penalty + sep_penalty, 4)

    dominant_pairs, weak_pairs = dimension_contributions(
        candidate_vector, role_vector
    )
    dominant = [
        label_dimension(dim) for dim, contrib in dominant_pairs if contrib > 0.02
    ]
    weak = [label_dimension(dim) for dim, _contrib in weak_pairs]

    # Missing = high role-family weight but low candidate contribution
    role_high = [
        label_dimension(d)
        for d in role_vector
        if role_vector[d] >= 0.2 and candidate_vector.get(d, 0.0) < 0.08
    ]
    missing_dims = list(dict.fromkeys(missing + role_high[:3]))[:4]

    semantic_distance = round(1.0 - proximity, 4)
    dom_labels = [label_dimension(d) for d, _ in dominant_pairs[:3]]
    weak_labels = [label_dimension(d) for d, _ in weak_pairs[:2]]
    explanation = recruiter_readable_explanation(
        family_id,
        proximity,
        dom_labels,
        weak_labels,
        missing_dims,
        cal_ctx.separation_v2 if cal_ctx else None,
        sep_penalty,
    )
    if neg_explanation and neg_penalty > 0:
        explanation = f"{explanation.rstrip('.')}. {neg_explanation}"
    if sep_explanation:
        explanation = f"{explanation.rstrip('.')}. {sep_explanation}"

    details: list[str] = []
    details.append(f"Cosine similarity: {raw_cosine:.3f}")
    if penalty > 0:
        details.append(f"Calibration penalty: −{penalty:.3f}")
    if neg_explanation and neg_penalty > 0:
        details.append(neg_explanation)
    if sep_explanation and sep_penalty > 0:
        details.append(sep_explanation)
    if dominant:
        details.append(f"Dominant: {', '.join(dominant)}")
    if missing_dims:
        details.append(f"Missing: {', '.join(missing_dims)}")

    return VectorProximityResult(
        proximity=proximity,
        semantic_distance=semantic_distance,
        distance=semantic_distance,
        dominant_dimensions=dominant,
        weak_dimensions=weak,
        missing_dimensions=missing_dims,
        explanation=explanation,
        detail_explanations=details,
        penalty_applied=penalty,
        raw_cosine=raw_cosine,
    )


def rank_role_families_by_vector(
    profile: CandidateProfile,
) -> list[tuple[RoleFamilyId, VectorProximityResult]]:
    """Rank all role families by vector proximity (higher = closer)."""
    cv_result = extract_candidate_vector(profile)
    cal_ctx = calibration_context_from_raw(cv_result.raw_scores)
    ranked: list[tuple[RoleFamilyId, VectorProximityResult]] = []

    for family_id in ROLE_FAMILIES:
        result = score_vector_proximity(
            cv_result.vector,
            family_id,
            raw_scores=cv_result.raw_scores,
            cal_ctx=cal_ctx,
        )
        ranked.append((family_id, result))

    return sorted(ranked, key=lambda x: -x[1].proximity)
