"""Deterministic contamination diagnostics for role-family scoring."""

from __future__ import annotations

from typing import Any

from career_intelligence_engine.intelligence.role_family_scoring import (
    UnifiedScoringResult,
    load_canonical_unified_from_profile,
)
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.evaluation import ContaminationSignal
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES

# Contamination families and their typical inflation triggers
_CONTAMINATION_FAMILIES: dict[str, tuple[RoleFamilyId, ...]] = {
    "HR": (RoleFamilyId.HR,),
    "Sales": (RoleFamilyId.SALES,),
    "Product": (RoleFamilyId.PRODUCT_MANAGEMENT, RoleFamilyId.PRODUCT_DELIVERY),
    "Operations": (RoleFamilyId.OPERATIONS, RoleFamilyId.ENTERPRISE_OPERATIONS),
    "Finance": (RoleFamilyId.FINANCE,),
}

# Generic language patterns that inflate cross-family scores
_GENERIC_INFLATION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("stakeholder", "generic stakeholder language inflating proximity"),
    ("cross-functional", "cross-functional delivery language overlap"),
    ("governance", "enterprise governance overlap"),
    ("delivery", "generic delivery language"),
    ("transformation", "broad transformation vocabulary"),
    ("operating model", "operating-model language overlap"),
    ("portfolio", "portfolio management language overlap"),
)

_CONTAMINATION_SCORE_RATIO = 0.65
_CONTAMINATION_TOP_N = 6


def _explain_contamination(
    contaminant: RoleFamilyId,
    primary: RoleFamilyId,
    contaminant_result,
    primary_result,
    cal_signals: list[str],
) -> list[str]:
    reasons: list[str] = []
    ratio = (
        contaminant_result.final_score / primary_result.final_score
        if primary_result.final_score > 0
        else 0.0
    )

    primary_def = ROLE_FAMILIES[primary]
    if contaminant in primary_def.excluded_families:
        reasons.append(
            f"{ROLE_FAMILIES[contaminant].display_name} is excluded from "
            f"{primary_def.display_name} but still scores {ratio:.0%} of primary."
        )
    elif contaminant in primary_def.far_families:
        reasons.append(
            f"Semantically distant family ({contaminant.value}) ranks high "
            f"despite far-family designation."
        )

    if contaminant == RoleFamilyId.FINANCE:
        if primary_result.ontology_score > 0 and "governance" in " ".join(
            cal_signals
        ).lower():
            reasons.append(
                "Finance proximity caused primarily by enterprise governance overlap."
            )
    if contaminant in (RoleFamilyId.OPERATIONS, RoleFamilyId.ENTERPRISE_OPERATIONS):
        if any("operational" in p.lower() or "delivery" in p.lower() for p, _ in _GENERIC_INFLATION_PATTERNS):
            reasons.append(
                "Operations proximity inflated by generic delivery language."
            )
    if contaminant in (RoleFamilyId.PRODUCT_MANAGEMENT, RoleFamilyId.PRODUCT_DELIVERY):
        reasons.append(
            "Product proximity inflated by roadmap or delivery vocabulary overlap."
        )
    if contaminant == RoleFamilyId.HR:
        reasons.append(
            "HR proximity inflated by people, culture, or organizational language."
        )
    if contaminant == RoleFamilyId.SALES:
        reasons.append(
            "Sales proximity inflated by revenue, pipeline, or client-facing language."
        )

    for penalty in contaminant_result.calibration_penalties:
        if "penalty" not in penalty.lower():
            continue
        if len(reasons) < 3:
            reasons.append(penalty)

    if not reasons:
        reasons.append(
            f"{ROLE_FAMILIES[contaminant].display_name} scores "
            f"{ratio:.0%} of primary without explicit exclusion."
        )
    return reasons[:4]


def analyze_contamination(
    profile: CandidateProfile,
    unified: UnifiedScoringResult | None = None,
) -> list[ContaminationSignal]:
    """Detect cross-family score inflation relative to declared primary."""
    if unified is None:
        unified = load_canonical_unified_from_profile(profile)
    if unified is None:
        return []

    primary = unified.primary
    primary_result = unified.results[primary]
    ranked = unified.ranked_by_final_score()
    rank_by_family = {fid: i + 1 for i, (fid, _) in enumerate(ranked)}
    cal_signals = list(profile.explanations.get("role_family_calibration") or [])

    signals: list[ContaminationSignal] = []
    seen_labels: set[str] = set()

    for label, families in _CONTAMINATION_FAMILIES.items():
        if label in seen_labels:
            continue
        for contaminant in families:
            if contaminant == primary:
                continue
            result = unified.results.get(contaminant)
            if result is None or result.final_score <= 0:
                continue
            rank = rank_by_family.get(contaminant, 99)
            if rank > _CONTAMINATION_TOP_N:
                continue
            ratio = (
                result.final_score / primary_result.final_score
                if primary_result.final_score > 0
                else 0.0
            )
            if ratio < _CONTAMINATION_SCORE_RATIO:
                continue
            reasons = _explain_contamination(
                contaminant,
                primary,
                result,
                primary_result,
                cal_signals,
            )
            signals.append(
                ContaminationSignal(
                    family=label,
                    contamination_score=round(min(1.0, ratio), 4),
                    reasons=reasons,
                )
            )
            seen_labels.add(label)
            break

    signals.sort(key=lambda s: -s.contamination_score)
    return signals


def contamination_to_trace_rows(
    signals: list[ContaminationSignal],
) -> list[dict[str, Any]]:
    return [s.to_dict() for s in signals]
