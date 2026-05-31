"""Confidence Calibration V2 and margin separation for enterprise delivery clusters."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.role_family_calibration import CalibrationContext

if TYPE_CHECKING:
    from career_intelligence_engine.intelligence.role_family_scoring import (
        RoleFamilyScoreResult,
        UnifiedScoringResult,
    )

# Enterprise delivery cluster — adjacent families that share partial vocabulary
DELIVERY_CLUSTER: frozenset[RoleFamilyId] = frozenset(
    {
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.ENTERPRISE_DELIVERY,
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.TRANSFORMATION_OFFICE,
    }
)

_TPM_TITLE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\btechnical program manager\b",
        r"\btechnical program management\b",
        r"\bsenior tpm\b",
        r"\btpm\b",
        r"\btechnical program lead\b",
    )
]

_EXPLICIT_RELEASE_TITLE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\brelease governance lead\b",
        r"\brelease manager\b",
        r"\brelease train engineer\b",
        r"\brelease management lead\b",
    )
]

_MAX_CLUSTER_PENALTY = -0.32
_MAX_CLUSTER_BONUS = 0.24

_TO_GOVERNANCE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\btransformation office\b",
        r"\boperating model redesign\b",
        r"\borg(?:anizational)? change governance\b",
        r"\bchange portfolio\b",
        r"\btransformation governance\b",
        r"\bbusiness transformation office\b",
    )
]


@dataclass
class MarginCalibrationResult:
    """Deterministic margin calibration trace."""

    dominance_margin: float = 0.0
    ambiguity_level: str = "HIGH"
    ranking_stability: float = 0.0
    adjustments: dict[str, float] = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)
    cluster_leader: str | None = None
    cluster_runner_up: str | None = None


@dataclass
class ConfidenceCalibrationV2:
    """Decomposed confidence signals for explainability."""

    score_margin_confidence: float = 0.0
    evidence_density_confidence: float = 0.0
    contamination_risk: float = 0.0
    ambiguity_penalty: float = 0.0
    calibration_strength: float = 0.0
    dominance_margin: float = 0.0
    ambiguity_level: str = "HIGH"
    ranking_stability: float = 0.0
    confidence_contributors: tuple[str, ...] = ()
    confidence_penalties: tuple[str, ...] = ()


def _corpus_from_ctx(cal_ctx: CalibrationContext) -> str:
    sep = cal_ctx.separation_v2
    return sep.corpus_lower if sep is not None else ""


def _gate(cal_ctx: CalibrationContext, family_id: RoleFamilyId) -> float:
    sep = cal_ctx.separation_v2
    if sep is None:
        return 0.0
    return float(sep.family_gate_scores.get(family_id.value, 0.0))


def _has_tpm_title(corpus: str) -> bool:
    return any(p.search(corpus) for p in _TPM_TITLE_PATTERNS)


def _has_explicit_release_title(corpus: str) -> bool:
    return any(p.search(corpus) for p in _EXPLICIT_RELEASE_TITLE_PATTERNS)


def _to_evidence_hits(corpus: str) -> int:
    return sum(len(p.findall(corpus)) for p in _TO_GOVERNANCE_PATTERNS)


def dominance_margin_bonus(
    *,
    leader_gate: float,
    runner_gate: float,
    title_aligned: bool,
    margin_ratio: float,
) -> float:
    """Bonus for gated primary when evidence and title align."""
    if leader_gate < 0.35:
        return 0.0
    bonus = 0.04
    if leader_gate >= 0.55:
        bonus += 0.06
    if leader_gate >= 0.75:
        bonus += 0.04
    if title_aligned:
        bonus += 0.05
    if runner_gate < 0.35:
        bonus += 0.03
    if margin_ratio < 0.06:
        bonus += 0.04
    return round(min(0.22, bonus), 4)


def adjacent_cluster_suppression(
    *,
    family_gate: float,
    leader_gate: float,
    partial_overlap: bool,
) -> float:
    """Penalty for adjacent cluster members with weak gated evidence."""
    if leader_gate < 0.35:
        return 0.0
    penalty = 0.06
    if partial_overlap:
        penalty += 0.08
    if family_gate < 0.25:
        penalty += 0.10
    elif family_gate < leader_gate - 0.20:
        penalty += 0.06
    if leader_gate >= 0.55 and family_gate < 0.45:
        penalty += 0.04
    return round(min(0.28, penalty), 4)


def gated_dominance_amplification(
    *,
    gate: float,
    is_leader: bool,
    cluster_tight: bool,
) -> float:
    """Amplify spread when gated evidence strongly favors one family."""
    if not is_leader or gate < 0.55:
        return 0.0
    amp = 0.05
    if gate >= 0.75:
        amp += 0.04
    if cluster_tight:
        amp += 0.05
    return round(min(0.14, amp), 4)


def low_evidence_flattening(
    *,
    score: float,
    gate: float,
    cluster_ceiling: float,
) -> float:
    """Pull low-gate adjacent scores toward cluster ceiling."""
    if gate >= 0.35:
        return score
    cap = max(0.0, cluster_ceiling - 0.12 - (0.35 - gate) * 0.15)
    return round(min(score, cap), 4)


def _cluster_scores(
    results: dict[RoleFamilyId, RoleFamilyScoreResult],
) -> list[tuple[RoleFamilyId, float]]:
    return sorted(
        (
            (fid, r.final_score)
            for fid, r in results.items()
            if fid in DELIVERY_CLUSTER and r.eligible_for_ranking and r.final_score > 0
        ),
        key=lambda x: -x[1],
    )


def apply_margin_calibration(
    results: dict[RoleFamilyId, RoleFamilyScoreResult],
    cal_ctx: CalibrationContext,
) -> MarginCalibrationResult:
    """
    Apply margin separation across the enterprise delivery cluster.

    Increases spread when gated evidence, titles, and partial-overlap rules
    favor one family over adjacent cluster members.
    """
    trace = MarginCalibrationResult()
    corpus = _corpus_from_ctx(cal_ctx)
    sep = cal_ctx.separation_v2

    tpm_gate = _gate(cal_ctx, RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT)
    release_gate = _gate(cal_ctx, RoleFamilyId.RELEASE_GOVERNANCE)
    delivery_gate = _gate(cal_ctx, RoleFamilyId.ENTERPRISE_DELIVERY)
    pl_gate = _gate(cal_ctx, RoleFamilyId.PROGRAM_LEADERSHIP)
    to_gate = _gate(cal_ctx, RoleFamilyId.TRANSFORMATION_OFFICE)

    raw = cal_ctx.raw_scores
    deliv_dim = float(raw.get("delivery_execution", 0.0))
    port_dim = float(raw.get("portfolio_management", 0.0))
    rel_dim = float(raw.get("release_governance", 0.0))

    tpm_title = _has_tpm_title(corpus)
    explicit_release_title = _has_explicit_release_title(corpus)
    to_hits = _to_evidence_hits(corpus)

    adjustments: dict[str, float] = {}

    def _apply(fid: RoleFamilyId, delta: float, signal: str) -> None:
        if abs(delta) < 0.001:
            return
        current = adjustments.get(fid.value, 0.0)
        if delta < 0 and current <= _MAX_CLUSTER_PENALTY + 0.001:
            return
        if delta > 0 and current >= _MAX_CLUSTER_BONUS - 0.001:
            return
        new_val = round(current + delta, 4)
        if delta < 0:
            new_val = max(_MAX_CLUSTER_PENALTY, new_val)
        else:
            new_val = min(_MAX_CLUSTER_BONUS, new_val)
        adjustments[fid.value] = new_val
        trace.signals.append(signal)

    # Rule: TPM titles dominate ancillary release-train language
    if tpm_title and not explicit_release_title:
        tpm_bonus = dominance_margin_bonus(
            leader_gate=max(tpm_gate, 0.55 if rel_dim >= 0.15 else tpm_gate),
            runner_gate=release_gate,
            title_aligned=True,
            margin_ratio=0.05,
        )
        if tpm_gate >= 0.35 or rel_dim >= 0.12:
            _apply(
                RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
                tpm_bonus,
                "tpm_title_dominance_margin_bonus",
            )
        release_penalty = adjacent_cluster_suppression(
            family_gate=release_gate,
            leader_gate=max(tpm_gate, 0.55),
            partial_overlap=release_gate >= 0.25 and release_gate < tpm_gate + 0.15,
        )
        if release_gate < 0.75 or tpm_gate >= release_gate - 0.10:
            _apply(
                RoleFamilyId.RELEASE_GOVERNANCE,
                -release_penalty,
                "release_partial_overlap_cluster_suppression",
            )

    # Rule: Release Governance requires explicit ownership signals
    if not explicit_release_title and release_gate < 0.55:
        _apply(
            RoleFamilyId.RELEASE_GOVERNANCE,
            -adjacent_cluster_suppression(
                family_gate=release_gate,
                leader_gate=max(tpm_gate, pl_gate, delivery_gate),
                partial_overlap=True,
            ),
            "release_weak_gate_suppression",
        )
    elif explicit_release_title and release_gate >= 0.55:
        amp = gated_dominance_amplification(
            gate=release_gate,
            is_leader=True,
            cluster_tight=True,
        )
        _apply(
            RoleFamilyId.RELEASE_GOVERNANCE,
            amp,
            "release_explicit_ownership_amplification",
        )
        if tpm_title and tpm_gate < release_gate - 0.12:
            _apply(
                RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
                -adjacent_cluster_suppression(
                    family_gate=tpm_gate,
                    leader_gate=release_gate,
                    partial_overlap=True,
                ),
                "tpm_suppressed_under_explicit_release_owner",
            )

    # Rule: Enterprise Delivery requires breadth, not TPM/release overlap alone
    if delivery_gate < 0.45 and deliv_dim < 0.22:
        if tpm_gate >= 0.45 or release_gate >= 0.45:
            _apply(
                RoleFamilyId.ENTERPRISE_DELIVERY,
                -adjacent_cluster_suppression(
                    family_gate=delivery_gate,
                    leader_gate=max(tpm_gate, release_gate),
                    partial_overlap=True,
                ),
                "enterprise_delivery_breadth_suppression",
            )
    elif delivery_gate >= 0.55 and deliv_dim >= 0.25:
        _apply(
            RoleFamilyId.ENTERPRISE_DELIVERY,
            gated_dominance_amplification(
                gate=delivery_gate,
                is_leader=delivery_gate >= max(tpm_gate, release_gate, pl_gate),
                cluster_tight=False,
            ),
            "enterprise_delivery_gated_amplification",
        )

    # Rule: Program Leadership requires PMO/portfolio governance
    if pl_gate < 0.45 and port_dim < 0.20:
        leader = max(tpm_gate, release_gate, delivery_gate)
        if leader >= 0.45:
            _apply(
                RoleFamilyId.PROGRAM_LEADERSHIP,
                -adjacent_cluster_suppression(
                    family_gate=pl_gate,
                    leader_gate=leader,
                    partial_overlap=True,
                ),
                "program_leadership_pmo_gate_suppression",
            )
    elif tpm_title and tpm_gate > pl_gate + 0.08 and pl_gate < 0.50:
        pl_penalty = adjacent_cluster_suppression(
            family_gate=pl_gate,
            leader_gate=tpm_gate,
            partial_overlap=True,
        )
        if pl_gate >= 0.45:
            pl_penalty = round(pl_penalty * 0.55, 4)
        _apply(
            RoleFamilyId.PROGRAM_LEADERSHIP,
            -pl_penalty,
            "program_leadership_tpm_title_suppression",
        )

    # Rule: Transformation Office requires org-change governance
    if to_gate < 0.55 and to_hits < 2:
        if sep and sep.delivery_governance_dominant:
            _apply(
                RoleFamilyId.TRANSFORMATION_OFFICE,
                -adjacent_cluster_suppression(
                    family_gate=to_gate,
                    leader_gate=max(tpm_gate, release_gate),
                    partial_overlap=True,
                ),
                "transformation_office_weak_org_change_suppression",
            )
    elif to_gate >= 0.55 or to_hits >= 2:
        _apply(
            RoleFamilyId.TRANSFORMATION_OFFICE,
            gated_dominance_amplification(
                gate=max(to_gate, 0.55 if to_hits >= 2 else to_gate),
                is_leader=to_gate >= max(tpm_gate, release_gate, pl_gate),
                cluster_tight=False,
            ),
            "transformation_office_governance_amplification",
        )

    # Cluster-wide: amplify leader / flatten weak gates when scores are tight
    ranked_before = _cluster_scores(results)
    cluster_tight = (
        len(ranked_before) >= 2
        and ranked_before[0][1] > 0
        and (ranked_before[0][1] - ranked_before[1][1]) / ranked_before[0][1] < 0.08
    )

    if ranked_before:
        leader_id, leader_score = ranked_before[0]
        leader_gate = _gate(cal_ctx, leader_id)
        if cluster_tight and leader_gate >= 0.55:
            _apply(
                leader_id,
                gated_dominance_amplification(
                    gate=leader_gate,
                    is_leader=True,
                    cluster_tight=True,
                ),
                "cluster_tight_gated_dominance_amplification",
            )
        for fid, score in ranked_before[1:4]:
            if fid == leader_id:
                continue
            fg = _gate(cal_ctx, fid)
            already_penalized = adjustments.get(fid.value, 0.0) <= -0.12
            if (
                fg < leader_gate - 0.20
                and fg < 0.45
                and not already_penalized
            ):
                _apply(
                    fid,
                    -adjacent_cluster_suppression(
                        family_gate=fg,
                        leader_gate=leader_gate,
                        partial_overlap=fg >= 0.20,
                    ),
                    f"adjacent_weak_gate_suppression:{fid.value}",
                )

    # Apply adjustments and low-evidence flattening
    cluster_ranked = _cluster_scores(results)
    cluster_top = cluster_ranked[0][1] if cluster_ranked else 0.0

    for fid, result in results.items():
        if fid not in DELIVERY_CLUSTER or not result.eligible_for_ranking:
            continue
        delta = adjustments.get(fid.value, 0.0)
        new_score = round(max(0.0, min(1.0, result.final_score + delta)), 4)
        fg = _gate(cal_ctx, fid)
        new_score = low_evidence_flattening(
            score=new_score,
            gate=fg,
            cluster_ceiling=cluster_top,
        )
        if abs(new_score - result.final_score) >= 0.001:
            result.final_score = new_score
            result.proximity = new_score
            result.semantic_distance = round(1.0 - new_score, 4)
            note = (
                f"Margin calibration V2: {fid.value} "
                f"{'+' if delta >= 0 else ''}{delta:.3f} → {new_score:.3f}"
            )
            if note not in result.calibration_penalties:
                result.calibration_penalties.append(note)

    ranked_after = _cluster_scores(results)
    if len(ranked_after) >= 2 and ranked_after[0][1] > 0:
        top, second = ranked_after[0][1], ranked_after[1][1]
        trace.dominance_margin = round(top - second, 4)
        trace.cluster_leader = ranked_after[0][0].value
        trace.cluster_runner_up = ranked_after[1][0].value
        ratio_gap = (top - second) / top
        trace.ranking_stability = round(min(1.0, ratio_gap * 2.5 + trace.dominance_margin), 4)
        if ratio_gap >= 0.12:
            trace.ambiguity_level = "LOW"
        elif ratio_gap >= 0.06:
            trace.ambiguity_level = "MEDIUM"
        else:
            trace.ambiguity_level = "HIGH"
    elif ranked_after:
        trace.dominance_margin = ranked_after[0][1]
        trace.cluster_leader = ranked_after[0][0].value
        trace.ranking_stability = 0.85
        trace.ambiguity_level = "LOW"

    trace.adjustments = adjustments
    return trace


def apply_margin_calibration_to_unified(
    unified: UnifiedScoringResult,
) -> MarginCalibrationResult:
    """Run margin calibration and attach trace to unified result."""
    margin = apply_margin_calibration(unified.results, unified.cal_ctx)
    unified.margin_calibration = margin
    return margin


def build_confidence_calibration_v2(
    profile,
    unified: UnifiedScoringResult,
    *,
    evidence_density: float,
    top_gap: float,
) -> ConfidenceCalibrationV2:
    """Compose V2 confidence from margin, evidence, gating, and contamination."""
    margin = getattr(unified, "margin_calibration", None)
    sep = unified.cal_ctx.separation_v2
    primary = unified.primary

    dominance_margin = margin.dominance_margin if margin else top_gap
    ambiguity_level = margin.ambiguity_level if margin else "HIGH"

    score_margin_confidence = max(0.0, min(1.0, dominance_margin * 2.2))
    if top_gap >= 0.15:
        score_margin_confidence = max(score_margin_confidence, 0.72)
    elif top_gap >= 0.08:
        score_margin_confidence = max(score_margin_confidence, 0.52)

    evidence_density_confidence = max(0.0, min(1.0, evidence_density))

    contamination_risk = 0.0
    if sep is not None:
        suppressed = len(sep.contamination_suppressed)
        if suppressed:
            contamination_risk = max(0.0, 0.35 - suppressed * 0.08)
        if sep.delivery_governance_dominant and not (
            sep.explicit_hr or sep.explicit_sales or sep.explicit_finance
        ):
            contamination_risk = min(contamination_risk, 0.25)
        else:
            contamination_risk = min(1.0, contamination_risk + 0.15)

    ambiguity_penalty = 0.0
    if ambiguity_level == "HIGH":
        ambiguity_penalty = 0.35
    elif ambiguity_level == "MEDIUM":
        ambiguity_penalty = 0.18
    if top_gap < 0.06:
        ambiguity_penalty = min(1.0, ambiguity_penalty + 0.20)

    primary_gate = (
        float(sep.family_gate_scores.get(primary.value, 0.0)) if sep else 0.0
    )
    calibration_strength = min(
        1.0,
        primary_gate * 0.5
        + (margin.ranking_stability if margin else 0.0) * 0.35
        + score_margin_confidence * 0.15,
    )

    contributors: list[str] = []
    penalties: list[str] = []

    if score_margin_confidence >= 0.55:
        contributors.append("score_margin_separation")
    if evidence_density_confidence >= 0.45:
        contributors.append("evidence_density")
    if primary_gate >= 0.55:
        contributors.append("gated_primary_evidence")
    if sep and sep.contamination_suppressed:
        contributors.append("contamination_suppressed")
    if margin and margin.dominance_margin >= 0.08:
        contributors.append("dominance_margin_calibrated")
    if calibration_strength >= 0.55:
        contributors.append("calibration_strength")

    if ambiguity_penalty >= 0.30:
        penalties.append("high_ambiguity_cluster")
    elif ambiguity_penalty >= 0.15:
        penalties.append("moderate_ambiguity_cluster")
    if contamination_risk >= 0.30:
        penalties.append("residual_contamination_risk")
    if primary_gate < 0.35 and sep is not None:
        penalties.append("weak_primary_gate")

    ranking_stability = margin.ranking_stability if margin else round(top_gap * 1.5, 4)

    return ConfidenceCalibrationV2(
        score_margin_confidence=round(score_margin_confidence, 4),
        evidence_density_confidence=round(evidence_density_confidence, 4),
        contamination_risk=round(contamination_risk, 4),
        ambiguity_penalty=round(ambiguity_penalty, 4),
        calibration_strength=round(calibration_strength, 4),
        dominance_margin=round(dominance_margin, 4),
        ambiguity_level=ambiguity_level,
        ranking_stability=round(ranking_stability, 4),
        confidence_contributors=tuple(contributors),
        confidence_penalties=tuple(penalties),
    )
