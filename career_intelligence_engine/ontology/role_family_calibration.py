"""Role-family ontology calibration — gates, negative constraints, explainable penalties."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from typing import Any

from career_intelligence_engine.intelligence.evidence_calibration import (
    EvidenceDepthResult,
    analyze_evidence_depth,
    frequency_to_score,
)
from career_intelligence_engine.models.ontology import ParsedResume, RoleFamilyId
from career_intelligence_engine.ontology.role_family_separation_v2 import (
    SeparationV2Context,
    apply_indirect_architecture_boost,
    build_separation_v2_context,
)

# Minimum raw dimension scores before role families receive full credit
DIMENSION_GATES: dict[str, float] = {
    "product_thinking": 0.20,
    "operational_management": 0.15,
    "architecture_coordination": 0.16,
    "portfolio_management": 0.18,
}

_PRODUCT_OWNERSHIP_PATTERNS = [
    re.compile(
        r"\b(product roadmap|roadmap ownership|owned the roadmap|product owner|"
        r"product strategy|feature prioritization|product-market fit)\b",
        re.I,
    ),
    re.compile(
        r"\b(customer discovery|user research|customer outcome|product vision|"
        r"go-to-market|gtm strategy|product kpi|product metrics)\b",
        re.I,
    ),
    re.compile(
        r"\b(prioritization framework|backlog ownership|product lifecycle|"
        r"market requirements|prd)\b",
        re.I,
    ),
]

_OPERATIONAL_RUNSTATE_PATTERNS = [
    re.compile(
        r"\b(run operations|operational continuity|sla management|incident management|"
        r"production support|noc |it operations manager)\b",
        re.I,
    ),
    re.compile(
        r"\b(business operations metrics|operational cadence|process ownership|"
        r"operational governance|service desk operations)\b",
        re.I,
    ),
]

# Delivery-only phrases that must NOT imply product ownership
_DELIVERY_ONLY_LEAKAGE = re.compile(
    r"\b(cross-functional delivery|agile|devops|stakeholder management|"
    r"program delivery|client delivery)\b",
    re.I,
)

# Generic ops leakage from program/delivery language
_OPS_FALSE_POSITIVE = re.compile(
    r"\b(operating model|process improvement|vendor management)\b",
    re.I,
)


@dataclass
class CalibrationContext:
    """Dimension evidence used for role-family gates and penalties."""

    raw_scores: dict[str, float] = field(default_factory=dict)
    product_ownership_depth: float = 0.0
    operational_run_depth: float = 0.0
    has_product_title: bool = False
    has_operations_title: bool = False
    signals: list[str] = field(default_factory=list)
    separation_v2: SeparationV2Context | None = None


def build_calibration_context(parsed: ParsedResume) -> CalibrationContext:
    """Derive calibration dimensions from resume text (deterministic)."""
    depth = analyze_evidence_depth(parsed)
    corpus = "\n".join(
        [parsed.raw_text] + parsed.bullets + parsed.job_titles
    ).lower()
    titles_lower = " ".join(parsed.job_titles).lower()

    product_hits = sum(len(p.findall(corpus)) for p in _PRODUCT_OWNERSHIP_PATTERNS)
    product_ownership = frequency_to_score(product_hits, strong=product_hits >= 3)
    if product_hits == 1:
        product_ownership = min(product_ownership, 0.12)
    elif product_hits == 2:
        product_ownership = min(product_ownership, 0.18)

    # Penalize if only delivery/agile language without product ownership vocabulary
    delivery_leak = len(_DELIVERY_ONLY_LEAKAGE.findall(corpus))
    if delivery_leak >= 2 and product_hits == 0:
        product_ownership = min(product_ownership, 0.08)

    ops_hits = sum(len(p.findall(corpus)) for p in _OPERATIONAL_RUNSTATE_PATTERNS)
    operational_run = frequency_to_score(ops_hits, strong=ops_hits >= 2)
    if ops_hits == 0:
        false_ops = len(_OPS_FALSE_POSITIVE.findall(corpus))
        if false_ops >= 1:
            operational_run = min(operational_run, 0.05)

    has_product_title = any(
        t in titles_lower
        for t in (
            "product manager",
            "product owner",
            "head of product",
            "director of product",
            "product delivery",
        )
    )
    has_operations_title = any(
        t in titles_lower
        for t in (
            "operations manager",
            "it operations",
            "service operations",
            "noc manager",
        )
    )

    from career_intelligence_engine.intelligence.candidate_vector import (
        _score_dimension_calibrated,
    )

    ownership = depth.ownership_strength
    raw: dict[str, float] = {}
    for dim in (
        "architecture_coordination",
        "portfolio_management",
        "delivery_execution",
        "technical_execution",
        "release_governance",
        "operational_management",
        "product_thinking",
    ):
        score, _ = _score_dimension_calibrated(corpus, dim, ownership_strength=ownership)
        raw[dim] = score

    raw["product_thinking"] = max(raw.get("product_thinking", 0.0), product_ownership)
    raw["operational_management"] = max(
        raw.get("operational_management", 0.0), operational_run
    )

    raw, arch_signals = apply_indirect_architecture_boost(raw, corpus)
    separation_v2 = build_separation_v2_context(corpus, raw)

    signals: list[str] = list(arch_signals)
    if product_hits == 0 and delivery_leak >= 2:
        signals.append("delivery_without_product_ownership")
    if ops_hits == 0 and operational_run < 0.1:
        signals.append("no_operational_run_state_evidence")

    return CalibrationContext(
        raw_scores=raw,
        product_ownership_depth=round(product_ownership, 3),
        operational_run_depth=round(operational_run, 3),
        has_product_title=has_product_title,
        has_operations_title=has_operations_title,
        signals=signals,
        separation_v2=separation_v2,
    )


@dataclass
class CalibrationPenalty:
    family_id: RoleFamilyId
    penalty_amount: float
    explanation: str


# Identity-score penalties (subtracted from ontology role_family scores)
_IDENTITY_PENALTIES: list[dict] = [
    {
        "families": [RoleFamilyId.PRODUCT_MANAGEMENT, RoleFamilyId.PRODUCT_DELIVERY],
        "gate": "product_thinking",
        "min": DIMENSION_GATES["product_thinking"],
        "unless_title": "product",
        "score_penalty": 18.0,
        "explanation": "Product track reduced due to missing roadmap and customer ownership evidence.",
    },
    {
        "families": [RoleFamilyId.OPERATIONS, RoleFamilyId.ENTERPRISE_OPERATIONS],
        "gate": "operational_management",
        "min": DIMENSION_GATES["operational_management"],
        "unless_title": "operations",
        "score_penalty": 22.0,
        "explanation": "Operations track reduced due to missing operational management evidence.",
    },
]

# Vector proximity penalties (additional to differentiation rules)
_VECTOR_NEGATIVE_CONSTRAINTS: dict[RoleFamilyId, dict] = {
    RoleFamilyId.PRODUCT_MANAGEMENT: {
        "gate": "product_thinking",
        "min": 0.20,
        "penalty": 0.48,
        "explanation": "Product Management proximity reduced due to missing roadmap ownership.",
        "unless_title_key": "product",
    },
    RoleFamilyId.PRODUCT_DELIVERY: {
        "gate": "product_thinking",
        "min": 0.18,
        "penalty": 0.42,
        "explanation": "Product Delivery proximity reduced due to missing product lifecycle ownership.",
        "unless_title_key": "product",
        "delivery_cap_without_product": True,
    },
    RoleFamilyId.OPERATIONS: {
        "gate": "operational_management",
        "min": 0.12,
        "zero_penalty": 0.50,
        "penalty": 0.45,
        "explanation": "Operations proximity reduced due to missing operational management evidence.",
        "unless_title_key": "operations",
    },
    RoleFamilyId.ENTERPRISE_OPERATIONS: {
        "gate": "operational_management",
        "min": 0.15,
        "zero_penalty": 0.48,
        "penalty": 0.42,
        "explanation": "Enterprise Operations proximity reduced due to missing run-state ownership.",
        "unless_title_key": "operations",
    },
}

# Primary-track preference when TPM/program evidence dominates
_ENTERPRISE_PROGRAM_FAMILIES = frozenset(
    {
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.ENTERPRISE_DELIVERY,
    }
)

_PRODUCT_FAMILIES = frozenset(
    {RoleFamilyId.PRODUCT_MANAGEMENT, RoleFamilyId.PRODUCT_DELIVERY}
)

_OPS_FAMILIES = frozenset(
    {RoleFamilyId.OPERATIONS, RoleFamilyId.ENTERPRISE_OPERATIONS}
)

_ARCH_HEAVY_FAMILIES = frozenset(
    {
        RoleFamilyId.ENTERPRISE_ARCHITECTURE_DELIVERY,
        RoleFamilyId.SOFTWARE_ENGINEERING,
        RoleFamilyId.PLATFORM_MODERNIZATION,
    }
)

PRODUCT_GATE = DIMENSION_GATES["product_thinking"]
OPS_GATE = DIMENSION_GATES["operational_management"]
ARCH_GATE = DIMENSION_GATES["architecture_coordination"]


def _product_gate_value(ctx: CalibrationContext) -> float:
    """Evidence-based product gate — keyword-only inflation cannot bypass ownership depth."""
    if ctx.has_product_title:
        return 1.0
    ownership = ctx.product_ownership_depth
    dim = ctx.raw_scores.get("product_thinking", 0.0)
    if ownership > 0 and dim > 0:
        return min(ownership, dim)
    return ownership if ownership > 0 else dim


def _operational_gate_value(ctx: CalibrationContext) -> float:
    """Strict operational gate — zero dimension blocks ops families."""
    if ctx.has_operations_title:
        return 1.0
    ops_dim = ctx.raw_scores.get("operational_management", 0.0)
    if ops_dim <= 0.0:
        return 0.0
    return max(ctx.operational_run_depth, ops_dim)


def compute_family_eligibility_flags(
    family_id: RoleFamilyId,
    ctx: CalibrationContext,
) -> tuple[bool, bool, bool, str]:
    """
    Stage-1 eligibility (authoritative exclusion, not score penalties).

    Returns (eligible_for_primary, eligible_for_adjacency, eligible_for_ranking, reason).
    """
    reasons: list[str] = []
    eligible_primary = True
    eligible_adjacency = True
    eligible_ranking = True

    product_val = _product_gate_value(ctx)
    ops_val = _operational_gate_value(ctx)
    arch_val = ctx.raw_scores.get("architecture_coordination", 0.0)
    tpm_signals = (
        ctx.raw_scores.get("technical_execution", 0.0) >= 0.15
        or ctx.raw_scores.get("release_governance", 0.0) >= 0.15
    )

    if family_id in _PRODUCT_FAMILIES:
        if product_val < PRODUCT_GATE:
            eligible_primary = False
            eligible_adjacency = False
            eligible_ranking = False
            reasons.append(
                f"product_thinking gate {product_val:.3f} < {PRODUCT_GATE} "
                "(missing roadmap/customer ownership evidence)"
            )
        elif family_id == RoleFamilyId.PRODUCT_DELIVERY and tpm_signals:
            if product_val < PRODUCT_GATE + 0.05:
                eligible_primary = False
                eligible_adjacency = False
                eligible_ranking = False
                reasons.append(
                    "TPM/release evidence without product lifecycle ownership"
                )

    if family_id in _OPS_FAMILIES:
        ops_dim = ctx.raw_scores.get("operational_management", 0.0)
        if ops_dim <= 0.0 and not ctx.has_operations_title:
            eligible_primary = False
            eligible_adjacency = False
            eligible_ranking = False
            reasons.append("operational_management dimension is zero")
        elif ops_val < OPS_GATE and not ctx.has_operations_title:
            eligible_primary = False
            eligible_adjacency = False
            eligible_ranking = False
            reasons.append(
                f"operational run-state evidence {ops_val:.3f} < {OPS_GATE}"
            )

    if family_id in _ARCH_HEAVY_FAMILIES:
        if arch_val <= 0.0:
            eligible_primary = False
            eligible_ranking = False
            reasons.append(
                f"architecture_coordination {arch_val:.3f} is zero — "
                "architecture-heavy family capped"
            )

    if ctx.separation_v2 is not None and ctx.separation_v2.delivery_governance_dominant:
        sep = ctx.separation_v2
        cluster_gate = max(
            sep.family_gate_scores.get(RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT.value, 0.0),
            sep.family_gate_scores.get(RoleFamilyId.RELEASE_GOVERNANCE.value, 0.0),
            sep.family_gate_scores.get(RoleFamilyId.PROGRAM_LEADERSHIP.value, 0.0),
            sep.family_gate_scores.get(RoleFamilyId.ENTERPRISE_DELIVERY.value, 0.0),
        )
        ai_trans_gate = sep.family_gate_scores.get(
            RoleFamilyId.AI_TRANSFORMATION.value, 0.0
        )
        if cluster_gate >= 0.55 and family_id in (
            RoleFamilyId.CLOUD_TRANSFORMATION,
            RoleFamilyId.DIGITAL_TRANSFORMATION,
        ):
            to_gate = sep.family_gate_scores.get(
                RoleFamilyId.TRANSFORMATION_OFFICE.value, 0.0
            )
            if to_gate < 0.55:
                eligible_adjacency = False
                reasons.append(
                    "V2: transformation family not eligible for adjacency on "
                    "delivery-governance profile"
                )
        if (
            family_id == RoleFamilyId.AI_PROGRAM_MANAGEMENT
            and cluster_gate >= 0.55
            and ai_trans_gate < 0.55
        ):
            eligible_adjacency = False
            reasons.append(
                "V2: AI Program Management not eligible for adjacency without "
                "AI transformation gated evidence"
            )

    reason = "; ".join(reasons)
    return eligible_primary, eligible_adjacency, eligible_ranking, reason


def build_eligibility_matrix(
    ctx: CalibrationContext,
) -> dict[str, dict[str, Any]]:
    """Per-family eligibility matrix for traceability."""
    from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES

    matrix: dict[str, dict[str, Any]] = {}
    for family_id in ROLE_FAMILIES:
        pri, adj, rank, reason = compute_family_eligibility_flags(family_id, ctx)
        matrix[family_id.value] = {
            "eligible_for_primary": pri,
            "eligible_for_adjacency": adj,
            "eligible_for_ranking": rank,
            "primary_track_eligible": pri,
            "adjacency_eligible": adj,
            "exclusion_reason": reason or None,
            "product_gate_value": round(_product_gate_value(ctx), 4),
            "operational_gate_value": round(_operational_gate_value(ctx), 4),
            "architecture_coordination": round(
                ctx.raw_scores.get("architecture_coordination", 0.0), 4
            ),
        }
    return matrix


def apply_family_eligibility(
    results: dict[RoleFamilyId, Any],
    ctx: CalibrationContext,
) -> list[RoleFamilyId]:
    """
    Stage 1 — apply hard eligibility filters before any ranking.

    Ineligible families are excluded from sorting (final_score zeroed).
    Returns list of family ids that became fully ineligible for ranking.
    """
    excluded: list[RoleFamilyId] = []
    for family_id, result in results.items():
        pri, adj, rank, reason = compute_family_eligibility_flags(family_id, ctx)

        result.eligible_for_primary = pri
        result.eligible_for_adjacency = adj
        result.eligible_for_ranking = rank
        result.primary_track_eligible = pri
        result.adjacency_eligible = adj
        result.primary_ineligible_reason = "" if pri else reason
        result.adjacency_ineligible_reason = "" if adj else reason

        if not rank:
            excluded.append(family_id)
            result.final_score = 0.0
            result.proximity = 0.0
            result.filtered = True
            result.filter_reason = reason or "Excluded by eligibility gate (stage 1)"
            if reason and reason not in result.calibration_penalties:
                result.calibration_penalties.append(
                    f"Eligibility exclusion: {reason}"
                )

    return excluded


def _gate_value(ctx: CalibrationContext, gate_dim: str) -> float:
    """Use ownership depths for gates — not inflated dimension keyword scores."""
    if gate_dim == "product_thinking":
        return ctx.product_ownership_depth
    if gate_dim == "operational_management":
        return max(
            ctx.operational_run_depth,
            ctx.raw_scores.get("operational_management", 0.0),
        )
    return ctx.raw_scores.get(gate_dim, 0.0)


def apply_identity_score_calibration(
    scores: dict[RoleFamilyId, float],
    ctx: CalibrationContext,
) -> tuple[dict[RoleFamilyId, float], list[CalibrationPenalty]]:
    """
    Deprecated — not used by canonical_unified_pipeline ranking.

    Retained for unit tests that assert gate penalty magnitudes on ontology scale.
    """
    adjusted = dict(scores)
    penalties: list[CalibrationPenalty] = []

    for rule in _IDENTITY_PENALTIES:
        gate_dim = rule["gate"]
        min_val = rule["min"]
        raw_val = _gate_value(ctx, gate_dim)
        title_ok = rule.get("unless_title") == "product" and ctx.has_product_title
        title_ok = title_ok or (
            rule.get("unless_title") == "operations" and ctx.has_operations_title
        )

        if raw_val >= min_val or title_ok:
            continue

        for family_id in rule["families"]:
            before = adjusted.get(family_id, 0.0)
            adjusted[family_id] = max(0.0, before - rule["score_penalty"])
            penalties.append(
                CalibrationPenalty(
                    family_id=family_id,
                    penalty_amount=rule["score_penalty"],
                    explanation=rule["explanation"],
                )
            )

    return adjusted, penalties


def resolve_primary_track(
    scores: dict[RoleFamilyId, float],
    ctx: CalibrationContext,
) -> RoleFamilyId:
    """
    Deprecated: use role_family_scoring.resolve_primary_from_unified instead.

    Legacy ontology-score primary selection (retained for tests only).
    """
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    if not ranked or ranked[0][1] <= 0:
        return RoleFamilyId.OPERATIONS

    product_min = DIMENSION_GATES["product_thinking"]
    tpm_signals = (
        ctx.raw_scores.get("technical_execution", 0.0) >= 0.15
        or ctx.raw_scores.get("release_governance", 0.0) >= 0.15
    )

    for family_id, score in ranked:
        if score <= 0:
            break
        if family_id in _PRODUCT_FAMILIES:
            if ctx.product_ownership_depth < product_min and not ctx.has_product_title:
                continue
            if family_id == RoleFamilyId.PRODUCT_DELIVERY and tpm_signals:
                if ctx.product_ownership_depth < product_min + 0.05:
                    continue
        if family_id in _OPS_FAMILIES:
            if ctx.operational_run_depth < DIMENSION_GATES["operational_management"]:
                if not ctx.has_operations_title:
                    continue
        return family_id

    return ranked[0][0]


def filter_adjacent_families(
    primary: RoleFamilyId,
    candidates: list[RoleFamilyId],
    ctx: CalibrationContext,
    scores: dict[RoleFamilyId, float],
) -> list[RoleFamilyId]:
    """Remove adjacency that violates dimension gates (stage-1 rules)."""
    filtered: list[RoleFamilyId] = []

    for family_id in candidates:
        if family_id == primary:
            continue
        _pri, adj, rank, _reason = compute_family_eligibility_flags(family_id, ctx)
        if not adj or not rank:
            continue
        if scores.get(family_id, 0.0) <= 0:
            continue
        filtered.append(family_id)

    return filtered


def calibration_context_from_raw(
    raw_scores: dict[str, float],
    *,
    has_product_title: bool = False,
    has_operations_title: bool = False,
    separation_v2: SeparationV2Context | None = None,
) -> CalibrationContext:
    """Rebuild calibration context from stored raw scores (vector scoring path)."""
    return CalibrationContext(
        raw_scores={
            k: v
            for k, v in raw_scores.items()
            if k in DIMENSION_GATES or k.endswith("_depth")
        },
        product_ownership_depth=raw_scores.get(
            "product_ownership_depth", raw_scores.get("product_thinking", 0.0)
        ),
        operational_run_depth=raw_scores.get(
            "operational_run_depth", raw_scores.get("operational_management", 0.0)
        ),
        has_product_title=has_product_title,
        has_operations_title=has_operations_title,
        separation_v2=separation_v2,
    )


def check_primary_eligibility(
    family_id: RoleFamilyId,
    ctx: CalibrationContext,
) -> tuple[bool, str]:
    """Whether family may be selected as primary career track."""
    pri, _adj, _rank, reason = compute_family_eligibility_flags(family_id, ctx)
    return pri, reason


def check_adjacency_eligibility(
    family_id: RoleFamilyId,
    ctx: CalibrationContext,
) -> tuple[bool, str]:
    """Whether family may appear in adjacent_role_families."""
    _pri, adj, _rank, reason = compute_family_eligibility_flags(family_id, ctx)
    return adj, reason


def apply_vector_negative_constraints(
    family_id: RoleFamilyId,
    proximity: float,
    raw_scores: dict[str, float],
    ctx: CalibrationContext | None,
) -> tuple[float, float, str | None]:
    """Additional proximity penalties from negative constraints."""
    rule = _VECTOR_NEGATIVE_CONSTRAINTS.get(family_id)
    if not rule or ctx is None:
        return proximity, 0.0, None

    gate = rule["gate"]
    min_val = rule["min"]
    if gate == "product_thinking":
        raw_val = max(raw_scores.get(gate, 0.0), ctx.product_ownership_depth)
    elif gate == "operational_management":
        raw_val = max(
            raw_scores.get(gate, 0.0),
            ctx.operational_run_depth,
            ctx.raw_scores.get("operational_management", 0.0),
        )
    else:
        raw_val = raw_scores.get(gate, 0.0)

    title_key = rule.get("unless_title_key")
    if title_key == "product" and ctx.has_product_title:
        return proximity, 0.0, None
    if title_key == "operations" and ctx.has_operations_title:
        return proximity, 0.0, None

    penalty = rule.get("penalty", 0.35)
    if raw_val <= 0.0 and rule.get("zero_penalty"):
        penalty = rule["zero_penalty"]
    elif raw_val < min_val:
        penalty = rule.get("penalty", 0.35)
    else:
        return proximity, 0.0, None

    # Product delivery: cap when delivery high but product low
    if rule.get("delivery_cap_without_product") and ctx.product_ownership_depth < min_val:
        delivery = raw_scores.get("delivery_execution", 0.0)
        if delivery >= 0.25:
            penalty = max(penalty, 0.40)

    adjusted = round(max(0.0, proximity - penalty), 4)
    return adjusted, penalty, rule["explanation"]
