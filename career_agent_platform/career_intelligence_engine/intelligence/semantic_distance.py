"""Ontology-driven semantic distance between role families."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES, get_role_family

# Enterprise transformation families that penalize engineering-only / HR / sales / finance adjacency
_ENTERPRISE_TRANSFORMATION_FAMILIES = {
    RoleFamilyId.AI_TRANSFORMATION,
    RoleFamilyId.TRANSFORMATION_OFFICE,
    RoleFamilyId.DIGITAL_TRANSFORMATION,
    RoleFamilyId.PROGRAM_LEADERSHIP,
    RoleFamilyId.AI_GOVERNANCE,
    RoleFamilyId.AI_PROGRAM_MANAGEMENT,
}

_FAR_FUNCTIONAL_FAMILIES = {
    RoleFamilyId.HR,
    RoleFamilyId.SALES,
    RoleFamilyId.FINANCE,
    RoleFamilyId.SOFTWARE_ENGINEERING,
}

_DIMENSION_WEIGHTS = {
    "governance": 0.20,
    "delivery": 0.15,
    "strategy": 0.15,
    "execution": 0.10,
    "transformation": 0.25,
    "signal_overlap": 0.15,
}


def _signal_set(defn) -> set[str]:
    return {
        s.lower()
        for s in (
            defn.positive_signals
            + defn.executive_signals
            + defn.archetype_keywords
            + defn.title_signals
        )
    }


def _negative_cross_penalty(source_def, target_def) -> float:
    """Penalize when source negatives align with target positives."""
    penalty = 0.0
    target_pos = _signal_set(target_def)
    for neg in source_def.negative_signals:
        neg_l = neg.lower()
        for pos in target_pos:
            if neg_l in pos or pos in neg_l:
                penalty += 0.12
    return min(0.45, penalty)


def _dimension_distance(source_def, target_def) -> float:
    """Weighted L1 distance across ontology dimension weights."""
    total = 0.0
    pairs = (
        ("governance", source_def.governance_weight, target_def.governance_weight),
        ("delivery", source_def.delivery_weight, target_def.delivery_weight),
        ("strategy", source_def.strategy_weight, target_def.strategy_weight),
        ("execution", source_def.execution_weight, target_def.execution_weight),
        ("transformation", source_def.transformation_weight, target_def.transformation_weight),
    )
    for key, a, b in pairs:
        total += abs(a - b) * _DIMENSION_WEIGHTS[key]
    return total


def _signal_overlap_distance(source_def, target_def) -> float:
    src = _signal_set(source_def)
    tgt = _signal_set(target_def)
    if not src or not tgt:
        return 0.5
    overlap = len(src & tgt) / len(src | tgt)
    return 1.0 - overlap


def _explicit_distance(source: RoleFamilyId, target: RoleFamilyId, source_def, target_def) -> float | None:
    """Return fixed distance when ontology declares explicit relationship."""
    if source == target:
        return 0.0
    if target in source_def.excluded_families or source in target_def.excluded_families:
        return 1.0
    if target in source_def.far_families or source in target_def.far_families:
        return 0.92
    if target in source_def.adjacent_families:
        return None  # compute, but cap as adjacent
    if source in target_def.adjacent_families:
        return None
    return None


def _enterprise_dominance_penalty(source: RoleFamilyId, target: RoleFamilyId, source_def) -> float:
    """Strong penalty when enterprise transformation source is paired with far functional roles."""
    if source not in _ENTERPRISE_TRANSFORMATION_FAMILIES:
        return 0.0
    if target not in _FAR_FUNCTIONAL_FAMILIES:
        return 0.0
    if source_def.transformation_weight >= 0.6 or source_def.governance_weight >= 0.7:
        if target == RoleFamilyId.SOFTWARE_ENGINEERING:
            return 0.25
        return 0.35
    return 0.15


def compute_family_distance(
    source_family: RoleFamilyId | str,
    target_family: RoleFamilyId | str,
) -> float:
    """
    Compute semantic distance between two role families.

    Returns 0.0 (identical) to 1.0 (extremely far). Considers signal overlap,
    executive/governance/transformation traits, and explicit far-family penalties.
    """
    if isinstance(source_family, str):
        source_family = RoleFamilyId(source_family)
    if isinstance(target_family, str):
        target_family = RoleFamilyId(target_family)

    if source_family == target_family:
        return 0.0

    source_def = get_role_family(source_family)
    target_def = get_role_family(target_family)

    explicit = _explicit_distance(source_family, target_family, source_def, target_def)
    if explicit is not None and explicit >= 0.9:
        return round(explicit, 3)
    if explicit == 0.0:
        return 0.0

    dim_dist = _dimension_distance(source_def, target_def)
    sig_dist = _signal_overlap_distance(source_def, target_def)
    neg_penalty = _negative_cross_penalty(source_def, target_def)
    ent_penalty = _enterprise_dominance_penalty(source_family, target_family, source_def)

    composite = (
        dim_dist * 0.55
        + sig_dist * _DIMENSION_WEIGHTS["signal_overlap"]
        + neg_penalty
        + ent_penalty
    )

    # Separation boost when families share adjacency but differ in transformation depth
    trans_gap = abs(source_def.transformation_weight - target_def.transformation_weight)
    if trans_gap >= 0.35:
        composite = max(composite, 0.38 + trans_gap * 0.15)

    # Adjacency caps — declared adjacent families stay in moderate-close range
    if target_family in source_def.adjacent_families:
        composite = min(composite, 0.68)
        composite = max(composite, 0.38)
    elif source_family in target_def.adjacent_families:
        composite = min(composite, 0.72)
        composite = max(composite, 0.40)

    # Far families never appear closer than 0.75 unless explicitly adjacent
    if target_family in source_def.far_families or source_family in target_def.far_families:
        composite = max(composite, 0.80)

    if target_family in source_def.excluded_families or source_family in target_def.excluded_families:
        composite = max(composite, 0.85)

    return round(min(1.0, max(0.0, composite)), 3)


def compute_adjacency_proximity(source_family: RoleFamilyId, target_family: RoleFamilyId) -> float:
    """Return proximity (1 - distance) for adjacency ranking."""
    return round(1.0 - compute_family_distance(source_family, target_family), 3)


def rank_families_by_distance(
    source_family: RoleFamilyId,
    candidates: list[RoleFamilyId] | None = None,
) -> list[tuple[RoleFamilyId, float]]:
    """Rank role families by semantic distance from source (ascending = closer)."""
    if candidates is None:
        candidates = list(ROLE_FAMILIES.keys())
    ranked = [(fid, compute_family_distance(source_family, fid)) for fid in candidates if fid != source_family]
    return sorted(ranked, key=lambda x: x[1])
