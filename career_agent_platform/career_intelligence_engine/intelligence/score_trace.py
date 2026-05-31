"""Deterministic score tracing — derived from unified role-family scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from career_intelligence_engine.intelligence.role_family_scoring import (
    SCORER_PATH,
    RoleFamilyScoreResult,
    build_score_trace_from_profile_unified,
    build_score_trace_from_unified,
    compute_unified_from_parsed,
)
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.ontology import ParsedResume, RoleFamilyId
from career_intelligence_engine.ontology.role_family_calibration import (
    CalibrationContext,
    CalibrationPenalty,
    build_calibration_context,
    check_adjacency_eligibility,
    check_primary_eligibility,
)

# Re-export eligibility checks (canonical implementation in role_family_calibration)
__all__ = [
    "RoleFamilyScoreTrace",
    "RoleFamilyScoreResult",
    "check_primary_eligibility",
    "check_adjacency_eligibility",
    "apply_identity_score_calibration_traced",
    "build_score_trace",
    "build_score_trace_from_profile",
    "SCORER_PATH",
]


@dataclass
class RoleFamilyScoreTrace:
    """Backward-compatible trace row (prefer RoleFamilyScoreResult)."""

    role_family: str
    display_name: str
    base_score: float = 0.0
    vector_score: float = 0.0
    penalties: list[str] = field(default_factory=list)
    boosts: list[str] = field(default_factory=list)
    semantic_distance_adjustment: float = 0.0
    calibrated_identity_score: float = 0.0
    final_score: float = 0.0
    filtered: bool = False
    filter_reason: str = ""
    primary_track_eligible: bool = True
    adjacency_eligible: bool = True
    is_primary: bool = False
    is_adjacent: bool = False
    scorer_path: str = SCORER_PATH

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def apply_identity_score_calibration_traced(
    scores: dict[RoleFamilyId, float],
    ctx: CalibrationContext,
) -> tuple[dict[RoleFamilyId, float], list[CalibrationPenalty], dict[RoleFamilyId, list[str]]]:
    """
    Deprecated: identity penalties on ontology scores are no longer used for ranking.

    Retained for unit tests that assert gate penalty behavior on ontology scale.
    """
    from career_intelligence_engine.ontology.role_family_calibration import (
        _IDENTITY_PENALTIES,
        _gate_value,
    )
    from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES

    adjusted = dict(scores)
    penalties: list[CalibrationPenalty] = []
    penalty_notes: dict[RoleFamilyId, list[str]] = {fid: [] for fid in ROLE_FAMILIES}

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
            msg = (
                f"Identity penalty −{rule['score_penalty']:.1f}: {rule['explanation']} "
                f"(gate {gate_dim}={raw_val:.3f} < {min_val})"
            )
            penalties.append(
                CalibrationPenalty(
                    family_id=family_id,
                    penalty_amount=rule["score_penalty"],
                    explanation=rule["explanation"],
                )
            )
            penalty_notes[family_id].append(msg)

    return adjusted, penalties, penalty_notes


def build_score_trace(
    parsed: ParsedResume,
    base_scores: dict[RoleFamilyId, float],
    *,
    primary: RoleFamilyId | None = None,
    adjacent: list[RoleFamilyId] | None = None,
    cal_ctx: CalibrationContext | None = None,
) -> list[dict[str, Any]]:
    """Build score trace from unified canonical scoring (legacy signature preserved)."""
    if cal_ctx is None:
        cal_ctx = build_calibration_context(parsed)

    unified = compute_unified_from_parsed(parsed, base_scores, cal_ctx=cal_ctx)
    if primary is not None or adjacent is not None:
        import warnings

        warnings.warn(
            "build_score_trace primary/adjacent overrides are deprecated; "
            "ranking is always resolved by the canonical unified pipeline.",
            DeprecationWarning,
            stacklevel=2,
        )
    return build_score_trace_from_unified(unified)


def build_score_trace_from_profile(profile: CandidateProfile) -> list[dict[str, Any]]:
    """Rehydrate trace from profile via unified scorer."""
    return build_score_trace_from_profile_unified(profile)
