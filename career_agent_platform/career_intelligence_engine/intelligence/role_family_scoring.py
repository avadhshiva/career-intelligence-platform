"""Unified role-family scoring — single canonical pipeline for all downstream outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from career_intelligence_engine.intelligence.candidate_vector import (
    CandidateVectorResult,
    extract_candidate_vector,
)
from career_intelligence_engine.intelligence.semantic_distance import compute_family_distance
from career_intelligence_engine.intelligence.vector_proximity import score_vector_proximity
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.ontology import ParsedResume, RoleFamilyId
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from career_intelligence_engine.intelligence.confidence_calibration_v2 import (
    MarginCalibrationResult,
    apply_margin_calibration,
)
from career_intelligence_engine.ontology.role_family_calibration import (
    CalibrationContext,
    CalibrationPenalty,
    apply_family_eligibility,
    build_calibration_context,
    build_eligibility_matrix,
    calibration_context_from_raw,
    filter_adjacent_families,
)

SCORER_PATH = "canonical_unified_pipeline"


@dataclass
class RoleFamilyScoreResult:
    """Canonical per-family score — all downstream outputs derive from this."""

    family: RoleFamilyId
    display_name: str
    ontology_score: float
    vector_score: float
    calibration_penalties: list[str] = field(default_factory=list)
    semantic_adjustments: list[str] = field(default_factory=list)
    final_score: float = 0.0
    proximity: float = 0.0
    semantic_distance: float = 0.0
    filtered: bool = False
    filter_reason: str = ""
    primary_track_eligible: bool = True
    adjacency_eligible: bool = True
    eligible_for_primary: bool = True
    eligible_for_adjacency: bool = True
    eligible_for_ranking: bool = True
    explanation: str = ""
    dominant_dimensions: list[str] = field(default_factory=list)
    weak_dimensions: list[str] = field(default_factory=list)
    missing_dimensions: list[str] = field(default_factory=list)
    is_primary: bool = False
    is_adjacent: bool = False
    scorer_path: str = SCORER_PATH
    primary_ineligible_reason: str = ""
    adjacency_ineligible_reason: str = ""

    def to_trace_dict(self) -> dict[str, Any]:
        """Serialize for score_trace / explanations (backward-compatible keys)."""
        return {
            "role_family": self.family.value,
            "display_name": self.display_name,
            "ontology_score": round(self.ontology_score, 3),
            "vector_score": round(self.vector_score, 4),
            "calibration_penalties": list(self.calibration_penalties),
            "semantic_adjustments": list(self.semantic_adjustments),
            "base_score": round(self.ontology_score, 3),
            "calibrated_identity_score": round(self.final_score, 4),
            "final_score": round(self.final_score, 4),
            "proximity": round(self.proximity, 4),
            "semantic_distance": round(self.semantic_distance, 4),
            "penalties": self.calibration_penalties + self.semantic_adjustments,
            "boosts": [],
            "semantic_distance_adjustment": round(
                self.vector_score - self.proximity, 4
            ),
            "filtered": self.filtered,
            "filter_reason": self.filter_reason,
            "primary_track_eligible": self.primary_track_eligible,
            "adjacency_eligible": self.adjacency_eligible,
            "eligible_for_primary": self.eligible_for_primary,
            "eligible_for_adjacency": self.eligible_for_adjacency,
            "eligible_for_ranking": self.eligible_for_ranking,
            "is_primary": self.is_primary,
            "is_adjacent": self.is_adjacent,
            "explanation": self.explanation,
            "scorer_path": self.scorer_path,
            "primary_ineligible_reason": self.primary_ineligible_reason,
            "adjacency_ineligible_reason": self.adjacency_ineligible_reason,
            "dominant_dimensions": list(self.dominant_dimensions),
            "weak_dimensions": list(self.weak_dimensions),
            "missing_dimensions": list(self.missing_dimensions),
        }


@dataclass
class UnifiedScoringResult:
    """Full scoring bundle for one candidate analysis."""

    results: dict[RoleFamilyId, RoleFamilyScoreResult]
    primary: RoleFamilyId
    adjacent: list[RoleFamilyId]
    cal_ctx: CalibrationContext
    identity_penalties: list[CalibrationPenalty] = field(default_factory=list)
    margin_calibration: MarginCalibrationResult | None = None

    def ranked_by_final_score(self) -> list[tuple[RoleFamilyId, float]]:
        return sorted(
            (
                (r.family, r.final_score)
                for r in self.results.values()
                if r.eligible_for_ranking
            ),
            key=lambda x: -x[1],
        )

    def final_scores_dict(self) -> dict[RoleFamilyId, float]:
        return {fid: r.final_score for fid, r in self.results.items()}


def _split_penalties(
    vp,
) -> tuple[list[str], list[str]]:
    """Separate calibration gate penalties from differentiation adjustments."""
    calibration: list[str] = []
    semantic: list[str] = []
    for line in vp.detail_explanations:
        lower = line.lower()
        if "penalty" in lower and (
            "roadmap" in lower
            or "operational" in lower
            or "product" in lower
            or "run-state" in lower
            or "lifecycle" in lower
            or "negative constraint" in lower
        ):
            calibration.append(line)
        elif "differentiation penalty" in lower:
            semantic.append(line)
        elif "cosine similarity" in lower:
            continue
        elif "dominant" in lower or "missing" in lower:
            semantic.append(line)
        else:
            semantic.append(line)

    if vp.penalty_applied > 0:
        diff_only = vp.penalty_applied
        neg_part = 0.0
        for line in vp.detail_explanations:
            if "roadmap" in line.lower() or "operational" in line.lower():
                neg_part = diff_only * 0.5
                break
        if not semantic and diff_only > 0:
            semantic.append(
                f"Differentiation penalty −{diff_only:.3f} "
                f"(cosine {vp.raw_cosine:.3f} → proximity {vp.proximity:.3f})"
            )
    return calibration, semantic


def _score_single_family(
    family_id: RoleFamilyId,
    ontology_score: float,
    candidate_vector: CandidateVectorResult,
    cal_ctx: CalibrationContext,
) -> RoleFamilyScoreResult:
    """Run vector scoring for one role family (eligibility applied in stage 1)."""
    merged_raw = dict(candidate_vector.raw_scores)
    merged_raw.update(cal_ctx.raw_scores)
    vp = score_vector_proximity(
        candidate_vector.vector,
        family_id,
        raw_scores=merged_raw,
        cal_ctx=cal_ctx,
    )

    calibration_penalties, semantic_adjustments = _split_penalties(vp)

    for line in vp.detail_explanations:
        lower = line.lower()
        if (
            "proximity reduced" in lower
            or "track reduced" in lower
            or "missing roadmap" in lower
            or "missing operational" in lower
            or "run-state" in lower
        ):
            if line not in calibration_penalties:
                calibration_penalties.append(line)

    return RoleFamilyScoreResult(
        family=family_id,
        display_name=ROLE_FAMILIES[family_id].display_name,
        ontology_score=round(ontology_score, 3),
        vector_score=round(vp.raw_cosine, 4),
        calibration_penalties=calibration_penalties,
        semantic_adjustments=semantic_adjustments,
        final_score=round(vp.proximity, 4),
        proximity=round(vp.proximity, 4),
        semantic_distance=round(vp.semantic_distance, 4),
        explanation=vp.explanation,
        dominant_dimensions=list(vp.dominant_dimensions),
        weak_dimensions=list(vp.weak_dimensions),
        missing_dimensions=list(vp.missing_dimensions),
        scorer_path=SCORER_PATH,
    )


def resolve_primary_from_unified(
    results: dict[RoleFamilyId, RoleFamilyScoreResult],
) -> RoleFamilyId:
    """Stage 2 — select primary only from eligible families."""
    from career_intelligence_engine.ontology.role_family_calibration import (
        _ENTERPRISE_PROGRAM_FAMILIES,
    )

    eligible = sorted(
        (
            r
            for r in results.values()
            if r.eligible_for_primary and r.eligible_for_ranking and r.final_score > 0
        ),
        key=lambda r: -r.final_score,
    )
    if eligible:
        return eligible[0].family

    program_cluster = sorted(
        (
            r
            for r in results.values()
            if r.family in _ENTERPRISE_PROGRAM_FAMILIES
            and r.eligible_for_ranking
            and r.final_score > 0
        ),
        key=lambda r: -r.final_score,
    )
    if program_cluster:
        return program_cluster[0].family

    any_ranked = sorted(
        (r for r in results.values() if r.eligible_for_ranking and r.final_score > 0),
        key=lambda r: -r.final_score,
    )
    if any_ranked:
        return any_ranked[0].family

    return RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT


def resolve_adjacent_from_unified(
    results: dict[RoleFamilyId, RoleFamilyScoreResult],
    primary: RoleFamilyId,
    cal_ctx: CalibrationContext,
) -> list[RoleFamilyId]:
    """Stage 2 — adjacent families from eligible pool only."""
    primary_result = results[primary]
    primary_def = ROLE_FAMILIES[primary]
    ranked = sorted(
        (
            r
            for r in results.values()
            if r.eligible_for_ranking and r.eligible_for_adjacency
        ),
        key=lambda r: -r.final_score,
    )

    adjacent: list[RoleFamilyId] = []
    primary_score = primary_result.final_score

    for r in ranked:
        if r.family == primary:
            continue
        if r.final_score <= 0:
            break
        if r.family in primary_def.excluded_families:
            continue
        if r.family in primary_def.far_families:
            continue

        sem = compute_family_distance(primary, r.family)
        if sem > 0.72:
            continue

        ratio = r.final_score / primary_score if primary_score else 0
        is_declared = r.family in primary_def.adjacent_families
        if ratio >= 0.45 or (is_declared and sem <= 0.65):
            adjacent.append(r.family)
        if len(adjacent) >= 5:
            break

    for adj in primary_def.adjacent_families:
        if adj in adjacent:
            continue
        adj_result = results.get(adj)
        if adj_result is None or adj_result.final_score <= 0:
            continue
        if not adj_result.eligible_for_adjacency or not adj_result.eligible_for_ranking:
            continue
        if adj in primary_def.excluded_families or adj in primary_def.far_families:
            continue
        if compute_family_distance(primary, adj) <= 0.65:
            adjacent.append(adj)

    adjacent.sort(key=lambda f: compute_family_distance(primary, f))
    final_scores = {fid: r.final_score for fid, r in results.items()}
    return filter_adjacent_families(primary, adjacent[:6], cal_ctx, final_scores)


def compute_unified_role_family_scores(
    ontology_scores: dict[RoleFamilyId, float],
    candidate_vector: CandidateVectorResult,
    cal_ctx: CalibrationContext,
) -> UnifiedScoringResult:
    """
    Canonical scoring pipeline:
    1. ontology scoring (input)
    2. capability vector scoring
    3. calibration penalties (vector layer)
    4. eligibility filtering (stage 1 — hard exclusion)
    5. ranking / primary / adjacency (stage 2 — eligible pool only)
    """
    cal_vec = calibration_context_from_raw(
        candidate_vector.raw_scores,
        has_product_title=cal_ctx.has_product_title,
        has_operations_title=cal_ctx.has_operations_title,
    )
    cal_vec.product_ownership_depth = cal_ctx.product_ownership_depth
    cal_vec.operational_run_depth = cal_ctx.operational_run_depth
    cal_vec.signals = cal_ctx.signals
    cal_vec.raw_scores = dict(cal_ctx.raw_scores)
    cal_vec.separation_v2 = cal_ctx.separation_v2

    results: dict[RoleFamilyId, RoleFamilyScoreResult] = {}
    for family_id in ROLE_FAMILIES:
        results[family_id] = _score_single_family(
            family_id,
            ontology_scores.get(family_id, 0.0),
            candidate_vector,
            cal_vec,
        )

    excluded = apply_family_eligibility(results, cal_vec)

    margin_calibration = apply_margin_calibration(results, cal_ctx)

    primary = resolve_primary_from_unified(results)
    adjacent = resolve_adjacent_from_unified(results, primary, cal_ctx)

    for fid, r in results.items():
        r.is_primary = fid == primary
        r.is_adjacent = fid in adjacent
        if not r.eligible_for_adjacency and fid in adjacent:
            r.filtered = True
            r.filter_reason = r.adjacency_ineligible_reason
        if not r.eligible_for_primary and not r.filter_reason:
            r.filter_reason = r.primary_ineligible_reason or ""

    return UnifiedScoringResult(
        results=results,
        primary=primary,
        adjacent=adjacent,
        cal_ctx=cal_ctx,
        margin_calibration=margin_calibration,
        identity_penalties=[
            CalibrationPenalty(
                family_id=fid,
                penalty_amount=0.0,
                explanation=results[fid].filter_reason,
            )
            for fid in excluded
            if results[fid].filter_reason
        ],
    )


def compute_unified_from_parsed(
    parsed: ParsedResume,
    ontology_scores: dict[RoleFamilyId, float],
    cal_ctx: CalibrationContext | None = None,
    interim_profile: CandidateProfile | None = None,
) -> UnifiedScoringResult:
    """Convenience entry: build vector + run unified pipeline from parsed resume."""
    if cal_ctx is None:
        cal_ctx = build_calibration_context(parsed)
    if interim_profile is None:
        interim_profile = CandidateProfile(top_skills=[])
    candidate_vector = extract_candidate_vector(interim_profile, parsed=parsed)
    return compute_unified_role_family_scores(
        ontology_scores, candidate_vector, cal_ctx
    )


def build_score_trace_from_unified(
    unified: UnifiedScoringResult,
) -> list[dict[str, Any]]:
    """Build score trace rows from the canonical scoring object."""
    traces: list[dict[str, Any]] = []
    for family_id in ROLE_FAMILIES:
        r = unified.results[family_id]
        traces.append(r.to_trace_dict())
    return traces


def build_canonical_ranking_snapshot(
    unified: UnifiedScoringResult,
    ontology_scores: dict[RoleFamilyId, float],
) -> dict[str, Any]:
    """Persist authoritative ranking for all downstream readers (UI, API, proximity)."""
    return {
        "scorer_path": SCORER_PATH,
        "primary": unified.primary.value,
        "adjacent": [a.value for a in unified.adjacent],
        "ontology_role_family_scores": {
            fid.value: round(ontology_scores.get(fid, 0.0), 3)
            for fid in ROLE_FAMILIES
        },
        "role_family_ranking": [
            {"family": fid.value, "score": round(score, 4)}
            for fid, score in unified.ranked_by_final_score()
        ],
        "eligibility_matrix": build_eligibility_matrix(unified.cal_ctx),
        "excluded_from_ranking": [
            fid.value
            for fid, r in unified.results.items()
            if not r.eligible_for_ranking
        ],
        "margin_calibration": (
            {
                "dominance_margin": unified.margin_calibration.dominance_margin,
                "ambiguity_level": unified.margin_calibration.ambiguity_level,
                "ranking_stability": unified.margin_calibration.ranking_stability,
                "cluster_leader": unified.margin_calibration.cluster_leader,
                "cluster_runner_up": unified.margin_calibration.cluster_runner_up,
                "adjustments": dict(unified.margin_calibration.adjustments),
                "signals": list(unified.margin_calibration.signals),
            }
            if unified.margin_calibration is not None
            else {}
        ),
        "families": {
            fid.value: unified.results[fid].to_trace_dict() for fid in ROLE_FAMILIES
        },
    }


def score_result_from_trace_dict(row: dict[str, Any]) -> RoleFamilyScoreResult:
    """Reconstruct canonical score row from stored snapshot."""
    family = RoleFamilyId(row["role_family"])
    return RoleFamilyScoreResult(
        family=family,
        display_name=row.get("display_name", ROLE_FAMILIES[family].display_name),
        ontology_score=float(row.get("ontology_score", row.get("base_score", 0))),
        vector_score=float(row.get("vector_score", 0)),
        calibration_penalties=list(row.get("calibration_penalties") or []),
        semantic_adjustments=[
            p
            for p in (row.get("penalties") or [])
            if p not in (row.get("calibration_penalties") or [])
        ],
        final_score=float(row.get("final_score", row.get("calibrated_identity_score", 0))),
        proximity=float(row.get("proximity", row.get("final_score", 0))),
        semantic_distance=float(row.get("semantic_distance", 0)),
        filtered=bool(row.get("filtered", False)),
        filter_reason=str(row.get("filter_reason") or ""),
        primary_track_eligible=bool(row.get("primary_track_eligible", True)),
        adjacency_eligible=bool(row.get("adjacency_eligible", True)),
        eligible_for_primary=bool(
            row.get("eligible_for_primary", row.get("primary_track_eligible", True))
        ),
        eligible_for_adjacency=bool(
            row.get("eligible_for_adjacency", row.get("adjacency_eligible", True))
        ),
        eligible_for_ranking=bool(row.get("eligible_for_ranking", True)),
        explanation=str(row.get("explanation") or ""),
        dominant_dimensions=list(row.get("dominant_dimensions") or []),
        weak_dimensions=list(row.get("weak_dimensions") or []),
        missing_dimensions=list(row.get("missing_dimensions") or []),
        is_primary=bool(row.get("is_primary", False)),
        is_adjacent=bool(row.get("is_adjacent", False)),
        scorer_path=SCORER_PATH,
        primary_ineligible_reason=str(row.get("primary_ineligible_reason") or ""),
        adjacency_ineligible_reason=str(row.get("adjacency_ineligible_reason") or ""),
    )


def load_canonical_unified_from_profile(
    profile: CandidateProfile,
) -> UnifiedScoringResult | None:
    """Load authoritative unified result from profile; None if missing or stale."""
    snap = profile.explanations.get("canonical_ranking")
    if not isinstance(snap, dict) or not snap.get("families"):
        return None
    path = snap.get("scorer_path")
    if path not in (SCORER_PATH, "unified_v1", "calibrated_v2"):
        return None

    results: dict[RoleFamilyId, RoleFamilyScoreResult] = {}
    for fid in ROLE_FAMILIES:
        row = snap["families"].get(fid.value)
        if row:
            results[fid] = score_result_from_trace_dict(row)

    if len(results) != len(ROLE_FAMILIES):
        return None

    primary = RoleFamilyId(snap["primary"])
    adjacent = [RoleFamilyId(a) for a in snap.get("adjacent", [])]
    cal_ctx = build_calibration_context_from_profile_explanations(profile)

    margin_calibration: MarginCalibrationResult | None = None
    mc_data = snap.get("margin_calibration") or profile.explanations.get(
        "margin_calibration_v2"
    )
    if isinstance(mc_data, dict) and mc_data:
        margin_calibration = MarginCalibrationResult(
            dominance_margin=float(mc_data.get("dominance_margin", 0.0)),
            ambiguity_level=str(mc_data.get("ambiguity_level", "HIGH")),
            ranking_stability=float(mc_data.get("ranking_stability", 0.0)),
            adjustments=dict(mc_data.get("adjustments") or {}),
            signals=list(mc_data.get("signals") or []),
            cluster_leader=mc_data.get("cluster_leader"),
            cluster_runner_up=mc_data.get("cluster_runner_up"),
        )

    return UnifiedScoringResult(
        results=results,
        primary=primary,
        adjacent=adjacent,
        cal_ctx=cal_ctx,
        margin_calibration=margin_calibration,
    )


def build_calibration_context_from_profile_explanations(
    profile: CandidateProfile,
) -> CalibrationContext:
    """Rebuild calibration context from analyze-time explanation fields."""
    return CalibrationContext(
        raw_scores=dict(profile.capability_raw_scores),
        product_ownership_depth=float(
            profile.explanations.get("product_ownership_depth") or 0.0
        ),
        operational_run_depth=float(
            profile.explanations.get("operational_run_depth") or 0.0
        ),
        has_product_title=bool(profile.explanations.get("has_product_title")),
        has_operations_title=bool(profile.explanations.get("has_operations_title")),
        signals=list(profile.explanations.get("role_family_calibration") or []),
    )


def get_score_trace_from_profile(profile: CandidateProfile) -> list[dict[str, Any]]:
    """Return stored score trace; never recompute with mislabeled final scores."""
    unified = load_canonical_unified_from_profile(profile)
    if unified is not None:
        return build_score_trace_from_unified(unified)
    stored = profile.explanations.get("score_trace")
    if isinstance(stored, list) and stored:
        for row in stored:
            row["scorer_path"] = SCORER_PATH
        return stored
    return []


def rank_role_families_from_profile(
    profile: CandidateProfile,
) -> list[tuple[RoleFamilyId, RoleFamilyScoreResult]]:
    """Authoritative proximity ranking — reads canonical snapshot only."""
    unified = load_canonical_unified_from_profile(profile)
    if unified is None:
        raise ValueError(
            "Profile has no canonical_ranking snapshot; re-analyze the resume "
            "through CareerIdentityEngine.analyze_parsed."
        )
    return sorted(
        (
            (fid, unified.results[fid])
            for fid in ROLE_FAMILIES
            if unified.results[fid].eligible_for_ranking
        ),
        key=lambda x: -x[1].final_score,
    ) + sorted(
        (
            (fid, unified.results[fid])
            for fid in ROLE_FAMILIES
            if not unified.results[fid].eligible_for_ranking
        ),
        key=lambda x: -x[1].ontology_score,
    )


def to_career_distance_result(
    result: RoleFamilyScoreResult,
) -> "CareerDistanceResult":
    """Map canonical score to CareerDistanceResult for API/UI proximity table."""
    from career_intelligence_engine.models.ontology import CareerDistanceResult

    explanation = [f"Scorer path: {result.scorer_path}"]
    explanation.extend(result.calibration_penalties)
    explanation.extend(result.semantic_adjustments)
    if result.explanation:
        explanation.append(result.explanation)

    return CareerDistanceResult(
        distance=result.semantic_distance,
        proximity=result.proximity,
        components={"vector_cosine": result.vector_score, "ontology_score": result.ontology_score},
        explanation=explanation,
        semantic_distance=result.semantic_distance,
        dominant_dimensions=list(result.dominant_dimensions),
        weak_dimensions=list(result.weak_dimensions),
        missing_dimensions=list(result.missing_dimensions),
        vector_explanation=result.explanation,
    )


def build_score_trace_from_profile_unified(
    profile: CandidateProfile,
) -> list[dict[str, Any]]:
    """Return authoritative score trace from profile snapshot (no legacy recompute)."""
    return get_score_trace_from_profile(profile)
