"""Deterministic confidence scoring for career identity inference."""

from __future__ import annotations

from career_intelligence_engine.intelligence.confidence_calibration_v2 import (
    build_confidence_calibration_v2,
)
from career_intelligence_engine.intelligence.role_family_scoring import (
    SCORER_PATH,
    UnifiedScoringResult,
    load_canonical_unified_from_profile,
)
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.evaluation import ConfidenceLevel, ConfidenceResult
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.capability_vectors import CAPABILITY_DIMENSIONS
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES


def _evidence_density(profile: CandidateProfile) -> float:
    vector = profile.capability_vector or {}
    if not vector:
        return 0.0
    non_zero = sum(1 for d in CAPABILITY_DIMENSIONS if float(vector.get(d, 0)) > 0.05)
    return min(1.0, non_zero / max(len(CAPABILITY_DIMENSIONS), 1))


def _ontology_vector_agreement(
    unified: UnifiedScoringResult,
    primary: RoleFamilyId,
) -> float:
    ontology_ranked = sorted(
        unified.results.items(),
        key=lambda x: -x[1].ontology_score,
    )
    vector_ranked = sorted(
        (
            (fid, r)
            for fid, r in unified.results.items()
            if r.eligible_for_ranking
        ),
        key=lambda x: -x[1].vector_score,
    )
    final_ranked = unified.ranked_by_final_score()

    ontology_top = ontology_ranked[0][0] if ontology_ranked else primary
    vector_top = vector_ranked[0][0] if vector_ranked else primary
    final_top = final_ranked[0][0] if final_ranked else primary

    matches = sum(
        1
        for a, b in ((ontology_top, primary), (vector_top, primary), (final_top, primary))
        if a == b
    )
    return matches / 3.0


def _eligibility_strength(unified: UnifiedScoringResult) -> float:
    total = len(unified.results)
    if total == 0:
        return 0.0
    eligible = sum(
        1
        for r in unified.results.values()
        if r.eligible_for_ranking and r.final_score > 0
    )
    return eligible / total


def _penalty_severity(unified: UnifiedScoringResult, primary: RoleFamilyId) -> float:
    primary_result = unified.results.get(primary)
    if primary_result is None:
        return 1.0
    penalty_count = len(primary_result.calibration_penalties) + len(
        primary_result.semantic_adjustments
    )
    return min(1.0, penalty_count / 6.0)


def _top_gap(unified: UnifiedScoringResult) -> float:
    ranked = unified.ranked_by_final_score()
    if len(ranked) < 2:
        return 1.0 if ranked else 0.0
    top1 = ranked[0][1]
    top2 = ranked[1][1]
    if top1 <= 0:
        return 0.0
    return max(0.0, min(1.0, (top1 - top2) / top1))


def compute_confidence(
    profile: CandidateProfile,
    unified: UnifiedScoringResult | None = None,
) -> ConfidenceResult:
    """Deterministic confidence from scoring signals (V2 margin + separation aware)."""
    if unified is None:
        unified = load_canonical_unified_from_profile(profile)
    if unified is None:
        return ConfidenceResult(
            confidence_score=0.0,
            confidence_level=ConfidenceLevel.LOW.value,
            ambiguity_score=1.0,
            evidence_density=0.0,
            top_gap=0.0,
        )

    primary = unified.primary
    gap = _top_gap(unified)
    density = _evidence_density(profile)
    eligibility = _eligibility_strength(unified)
    agreement = _ontology_vector_agreement(unified, primary)
    penalty = _penalty_severity(unified, primary)

    excluded_count = sum(
        1 for r in unified.results.values() if not r.eligible_for_ranking
    )
    exclusion_factor = max(0.0, 1.0 - excluded_count / max(len(ROLE_FAMILIES), 1) * 0.5)

    sep = unified.cal_ctx.separation_v2
    cal_v2 = build_confidence_calibration_v2(
        profile, unified, evidence_density=density, top_gap=gap
    )

    contributors = list(cal_v2.confidence_contributors)
    penalties = list(cal_v2.confidence_penalties)

    primary_gate = 0.0
    if sep is not None:
        primary_gate = float(sep.family_gate_scores.get(primary.value, 0.0))
        if primary_gate >= 0.55 and "gated_primary_evidence" not in contributors:
            contributors.append("gated_primary_evidence")
        if sep.contamination_suppressed and "contamination_suppressed" not in contributors:
            contributors.append("contamination_suppressed")
        if sep.delivery_governance_dominant and not (
            sep.explicit_hr or sep.explicit_sales or sep.explicit_finance
        ):
            if "delivery_profile_clarity" not in contributors:
                contributors.append("delivery_profile_clarity")

    dominance_margin = cal_v2.dominance_margin
    if unified.margin_calibration is not None:
        dominance_margin = unified.margin_calibration.dominance_margin

    if gap >= 0.18 and "wide_top_gap" not in contributors:
        contributors.append("wide_top_gap")
    if excluded_count >= 3 and "eligibility_exclusions_reduce_ambiguity" not in contributors:
        contributors.append("eligibility_exclusions_reduce_ambiguity")

    ambiguity = min(1.0, cal_v2.ambiguity_penalty + (1.0 - gap) * 0.35)
    if gap < 0.08 and "narrow_top_gap" not in penalties:
        penalties.append("narrow_top_gap")
    elif gap < 0.15 and "moderate_top_gap" not in penalties:
        penalties.append("moderate_top_gap")

    if agreement < 0.34 and "ontology_vector_disagreement" not in penalties:
        penalties.append("ontology_vector_disagreement")

    sep_boost = 0.0
    if "gated_primary_evidence" in contributors:
        sep_boost += 0.08
    if "contamination_suppressed" in contributors:
        sep_boost += 0.06
    if "wide_top_gap" in contributors:
        sep_boost += 0.05
    if "dominance_margin_calibrated" in contributors:
        sep_boost += 0.06
    if "score_margin_separation" in contributors:
        sep_boost += 0.05

    raw_score = (
        cal_v2.score_margin_confidence * 0.22
        + cal_v2.evidence_density_confidence * 0.16
        + cal_v2.calibration_strength * 0.18
        + gap * 0.14
        + eligibility * 0.10
        + agreement * 0.10
        + (1.0 - penalty) * 0.05
        + exclusion_factor * 0.05
        + sep_boost
    )
    raw_score *= max(0.55, 1.0 - cal_v2.contamination_risk * 0.35)
    confidence_score = max(0.0, min(1.0, raw_score * (1.0 - ambiguity * 0.20)))

    if gap < 0.06 and agreement < 0.34 and cal_v2.ambiguity_level == "HIGH":
        level = ConfidenceLevel.AMBIGUOUS
    elif confidence_score >= 0.72 and gap >= 0.15:
        level = ConfidenceLevel.HIGH
    elif confidence_score >= 0.48 and gap >= 0.08:
        level = ConfidenceLevel.MEDIUM
    elif confidence_score >= 0.30:
        level = ConfidenceLevel.LOW
    else:
        level = ConfidenceLevel.AMBIGUOUS

    return ConfidenceResult(
        confidence_score=round(confidence_score, 4),
        confidence_level=level.value,
        ambiguity_score=round(ambiguity, 4),
        evidence_density=round(density, 4),
        top_gap=round(gap, 4),
        confidence_contributors=tuple(contributors),
        confidence_penalties=tuple(penalties),
        dominance_margin=round(dominance_margin, 4),
        ambiguity_level=cal_v2.ambiguity_level,
        ranking_stability=cal_v2.ranking_stability,
        score_margin_confidence=cal_v2.score_margin_confidence,
        evidence_density_confidence=cal_v2.evidence_density_confidence,
        contamination_risk=cal_v2.contamination_risk,
        ambiguity_penalty=cal_v2.ambiguity_penalty,
        calibration_strength=cal_v2.calibration_strength,
    )


def attach_confidence_to_explanations(
    profile: CandidateProfile,
    confidence: ConfidenceResult,
) -> None:
    profile.explanations["confidence"] = confidence.to_dict()
    profile.explanations.setdefault("scorer_path", SCORER_PATH)
