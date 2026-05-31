"""Orchestrates resume parsing and deterministic career identity inference."""

from __future__ import annotations

import logging
from typing import Any

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.ontology import ParsedResume, RoleFamilyId
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from career_intelligence_engine.parsing.resume_parser import ResumeParser
from career_intelligence_engine.parsing.skill_extractor import SkillExtractor
from career_intelligence_engine.intelligence.domain_inference import DomainInference
from career_intelligence_engine.intelligence.leadership_inference import LeadershipInference
from career_intelligence_engine.intelligence.seniority_inference import SeniorityInference
from career_intelligence_engine.intelligence.capability_density import (
    score_capability_density,
    score_text_for_family,
)
from career_intelligence_engine.intelligence.executive_signals import detect_executive_signals
from career_intelligence_engine.intelligence.semantic_distance import compute_family_distance
from career_intelligence_engine.intelligence.transformation_inference import (
    TransformationInference,
)
from career_intelligence_engine.intelligence.candidate_vector import extract_candidate_vector
from career_intelligence_engine.intelligence.explainability import humanize_signals
from career_intelligence_engine.intelligence.confidence import (
    attach_confidence_to_explanations,
    compute_confidence,
)
from career_intelligence_engine.intelligence.contamination_analysis import (
    analyze_contamination,
    contamination_to_trace_rows,
)
from career_intelligence_engine.intelligence.gap_analysis import analyze_capability_gaps
from career_intelligence_engine.intelligence.role_family_scoring import (
    SCORER_PATH,
    build_canonical_ranking_snapshot,
    build_score_trace_from_unified,
    compute_unified_from_parsed,
)
from career_intelligence_engine.ontology.role_family_calibration import (
    build_calibration_context,
)

logger = logging.getLogger(__name__)

_TITLE_WEIGHT = 3.0
_EXPERIENCE_WEIGHT = 1.5
_SKILL_WEIGHT = 1.0
_RECENCY_BOOST = 1.5


class CareerIdentityEngine:
    """
    End-to-end pipeline: resume → ParsedResume → CandidateProfile.
    All steps are rule-based and logged with explanations.
    """

    def __init__(self) -> None:
        self._parser = ResumeParser()
        self._skills = SkillExtractor()
        self._seniority = SeniorityInference()
        self._leadership = LeadershipInference()
        self._domain = DomainInference()
        self._transformation = TransformationInference()

    def analyze_bytes(self, content: bytes, filename: str) -> CandidateProfile:
        parsed = self._parser.parse_bytes(content, filename)
        return self.analyze_parsed(parsed)

    def analyze_text(self, text: str) -> CandidateProfile:
        parsed = self._parser.parse_text(text)
        return self.analyze_parsed(parsed)

    def analyze_parsed(self, parsed: ParsedResume) -> CandidateProfile:
        skill_data = self._skills.extract(parsed.raw_text, parsed.bullets)
        seniority_result = self._seniority.infer(parsed)
        leadership_result = self._leadership.infer(parsed, seniority_result.level)
        domain_result = self._domain.infer(parsed, skill_data)
        transform_result = self._transformation.infer(parsed)
        executive_result = detect_executive_signals(parsed)

        cal_ctx = build_calibration_context(parsed)
        ontology_scores = self._score_role_families(
            parsed, skill_data, executive_result
        )
        interim = CandidateProfile(
            top_skills=skill_data.get("top_skills", []),
            governance_experience=leadership_result.governance_experience,
            stakeholder_complexity=leadership_result.stakeholder_complexity,
            execution_orientation=leadership_result.execution_orientation,
            strategic_orientation=leadership_result.strategic_orientation,
            transformation_focus=transform_result.transformation_focus,
            ai_maturity=transform_result.ai_maturity,
            enterprise_experience=domain_result.enterprise_experience,
            delivery_orientation=domain_result.delivery_orientation,
            leadership_level=leadership_result.level,
        )
        unified = compute_unified_from_parsed(
            parsed,
            ontology_scores,
            cal_ctx=cal_ctx,
            interim_profile=interim,
        )
        primary_track = unified.primary
        adjacent = unified.adjacent
        role_scores = unified.final_scores_dict()
        score_trace = build_score_trace_from_unified(unified)
        canonical_ranking = build_canonical_ranking_snapshot(unified, ontology_scores)
        candidate_vector = extract_candidate_vector(interim, parsed=parsed)
        interim_scored = interim.model_copy(
            update={
                "capability_vector": candidate_vector.vector,
                "capability_raw_scores": candidate_vector.raw_scores,
            }
        )
        confidence = compute_confidence(interim_scored, unified=unified)
        contamination_signals = analyze_contamination(interim_scored, unified=unified)
        gap_primary = analyze_capability_gaps(
            candidate_vector.vector, primary_track
        )

        profile = CandidateProfile(
            full_name=parsed.full_name,
            years_experience=parsed.years_experience,
            current_seniority=seniority_result.level,
            leadership_level=leadership_result.level,
            primary_career_track=primary_track,
            adjacent_role_families=adjacent,
            primary_domains=domain_result.primary_domains,
            secondary_domains=domain_result.secondary_domains,
            enterprise_experience=domain_result.enterprise_experience,
            delivery_orientation=domain_result.delivery_orientation,
            transformation_focus=transform_result.transformation_focus,
            ai_maturity=transform_result.ai_maturity,
            likely_target_company_archetypes=domain_result.company_archetypes,
            inferred_locations=parsed.locations,
            top_skills=skill_data.get("top_skills", []),
            governance_experience=leadership_result.governance_experience,
            stakeholder_complexity=leadership_result.stakeholder_complexity,
            execution_orientation=leadership_result.execution_orientation,
            strategic_orientation=leadership_result.strategic_orientation,
            role_family_scores={k.value: round(v, 2) for k, v in role_scores.items()},
            capability_vector=candidate_vector.vector,
            capability_raw_scores=candidate_vector.raw_scores,
            confidence_result=confidence,
            explanations=self._build_explanations(
                seniority_result.signals,
                leadership_result.signals,
                domain_result.signals,
                transform_result.signals,
                executive_result,
                primary_track,
                adjacent,
                role_scores,
                cal_ctx,
                unified,
                score_trace,
                canonical_ranking,
                ontology_scores,
            ),
        )
        attach_confidence_to_explanations(profile, confidence)
        profile.explanations["contamination_signals"] = contamination_to_trace_rows(
            contamination_signals
        )
        profile.explanations["gap_analysis_primary"] = gap_primary.to_dict()
        if unified.cal_ctx.separation_v2 is not None:
            sep = unified.cal_ctx.separation_v2
            profile.explanations["separation_v2"] = {
                "signals": list(sep.signals),
                "family_gate_scores": dict(sep.family_gate_scores),
                "contamination_suppressed": list(sep.contamination_suppressed),
                "delivery_governance_dominant": sep.delivery_governance_dominant,
            }
        if unified.margin_calibration is not None:
            mc = unified.margin_calibration
            profile.explanations["margin_calibration_v2"] = {
                "dominance_margin": mc.dominance_margin,
                "ambiguity_level": mc.ambiguity_level,
                "ranking_stability": mc.ranking_stability,
                "cluster_leader": mc.cluster_leader,
                "cluster_runner_up": mc.cluster_runner_up,
                "adjustments": dict(mc.adjustments),
                "signals": list(mc.signals),
            }
        if score_trace:
            for row in score_trace:
                if row.get("is_primary"):
                    row["confidence_level"] = confidence.confidence_level
                    row["confidence_score"] = confidence.confidence_score
        logger.info(
            "Career identity: track=%s seniority=%s leadership=%s",
            profile.primary_career_track.value,
            profile.current_seniority.value,
            profile.leadership_level.value,
        )
        return profile

    def _score_role_families(
        self,
        parsed: ParsedResume,
        skill_data: dict[str, Any],
        executive_result,
    ) -> dict[RoleFamilyId, float]:
        text = parsed.raw_text.lower()
        titles_all = " ".join(parsed.job_titles).lower()
        recent_title = (parsed.job_titles[0] if parsed.job_titles else "").lower()
        bullets = parsed.bullets
        bullets_text = "\n".join(bullets).lower()
        top_skills = " ".join(skill_data.get("top_skills", [])).lower()

        density = score_capability_density(text, bullets)
        scores: dict[RoleFamilyId, float] = {fid: 0.0 for fid in ROLE_FAMILIES}

        for family_id, definition in ROLE_FAMILIES.items():
            # Ontology-driven density scoring with positive/negative signals
            semantic_score = score_text_for_family(
                text,
                bullets,
                definition.positive_signals,
                definition.negative_signals,
            )
            scores[family_id] += semantic_score * (1.0 + density.total_density * 0.5)

            for title in definition.canonical_titles:
                if title in titles_all:
                    w = _TITLE_WEIGHT * (_RECENCY_BOOST if title in recent_title else 1.0)
                    scores[family_id] += w
            for sig in definition.title_signals:
                if sig in recent_title:
                    scores[family_id] += _TITLE_WEIGHT * _RECENCY_BOOST
                elif sig in titles_all:
                    scores[family_id] += _TITLE_WEIGHT
            for sig in definition.experience_signals:
                if sig in text or sig in bullets_text:
                    scores[family_id] += _EXPERIENCE_WEIGHT
            for sig in definition.skill_signals:
                if sig in top_skills or sig in text:
                    scores[family_id] += _SKILL_WEIGHT

            # Executive signal boost for governance/transformation-heavy families
            exec_boost = (
                executive_result.executive_strength * definition.governance_weight * 2.0
                + executive_result.transformation_leadership
                * definition.transformation_weight
                * 2.5
                + executive_result.enterprise_governance * definition.delivery_weight * 1.5
            )
            scores[family_id] += exec_boost

        return scores

    def _build_explanations(
        self,
        seniority_signals: list[str],
        leadership_signals: list[str],
        domain_signals: list[str],
        transform_signals: list[str],
        executive_result,
        primary: RoleFamilyId,
        adjacent: list[RoleFamilyId],
        role_scores: dict[RoleFamilyId, float],
        cal_ctx=None,
        unified=None,
        score_trace: list | None = None,
        canonical_ranking: dict | None = None,
        ontology_scores: dict[RoleFamilyId, float] | None = None,
    ) -> dict[str, Any]:
        top_scores = unified.ranked_by_final_score()[:5] if unified else sorted(
            role_scores.items(), key=lambda x: -x[1]
        )[:5]
        calibration_notes = []
        if unified is not None:
            for r in unified.results.values():
                calibration_notes.extend(r.calibration_penalties)
        if cal_ctx is not None:
            calibration_notes.extend(cal_ctx.signals)
        return {
            "seniority": humanize_signals(seniority_signals, "seniority"),
            "leadership": humanize_signals(leadership_signals, "leadership"),
            "domain": humanize_signals(domain_signals, "domain"),
            "transformation": humanize_signals(transform_signals, "transformation"),
            "executive": executive_result.human_readable,
            "primary_career_track": {
                "family": primary.value,
                "display": ROLE_FAMILIES[primary].display_name,
                "reason": (
                    "Highest unified final score combining ontology signals, "
                    "capability vector proximity, and calibration gates."
                ),
            },
            "adjacent_role_families": [
                {
                    "family": a.value,
                    "display": ROLE_FAMILIES[a].display_name,
                    "semantic_distance": compute_family_distance(primary, a),
                }
                for a in adjacent
            ],
            "role_family_ranking": (
                canonical_ranking["role_family_ranking"]
                if canonical_ranking
                else [
                    {"family": f.value, "score": round(s, 2)}
                    for f, s in top_scores
                ]
            ),
            "canonical_ranking": canonical_ranking or {},
            "ontology_role_family_scores": (
                {
                    fid.value: round(score, 3)
                    for fid, score in (ontology_scores or {}).items()
                }
                if ontology_scores
                else {}
            ),
            "role_family_calibration": calibration_notes,
            "product_ownership_depth": (
                round(cal_ctx.product_ownership_depth, 3) if cal_ctx else None
            ),
            "operational_run_depth": (
                round(cal_ctx.operational_run_depth, 3) if cal_ctx else None
            ),
            "has_product_title": cal_ctx.has_product_title if cal_ctx else False,
            "has_operations_title": cal_ctx.has_operations_title if cal_ctx else False,
            "score_trace": score_trace or [],
            "scorer_path": SCORER_PATH,
            "eligibility_matrix": (
                canonical_ranking.get("eligibility_matrix") if canonical_ranking else {}
            ),
            "excluded_from_ranking": (
                canonical_ranking.get("excluded_from_ranking") if canonical_ranking else []
            ),
        }
