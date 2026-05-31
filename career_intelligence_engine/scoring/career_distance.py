"""Career proximity scoring — role-family graph, not keyword overlap."""

from __future__ import annotations

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.ontology import (
    CareerDistanceInput,
    CareerDistanceResult,
    EnterpriseExposure,
    LeadershipLevel,
    RoleFamilyId,
    SeniorityLevel,
)
from career_intelligence_engine.intelligence.semantic_distance import compute_family_distance
from career_intelligence_engine.intelligence.candidate_vector import extract_candidate_vector
from career_intelligence_engine.intelligence.vector_proximity import (
    VectorProximityResult,
    score_vector_proximity,
)
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES


def _career_distance_from_vector(vp: VectorProximityResult) -> CareerDistanceResult:
    """Map vector proximity output to a fully populated CareerDistanceResult."""
    return CareerDistanceResult(
        distance=vp.distance,
        proximity=vp.proximity,
        components={"vector_cosine": vp.raw_cosine},
        explanation=list(vp.detail_explanations),
        semantic_distance=vp.semantic_distance,
        dominant_dimensions=list(vp.dominant_dimensions),
        weak_dimensions=list(vp.weak_dimensions),
        missing_dimensions=list(vp.missing_dimensions),
        vector_explanation=vp.explanation,
    )


def _career_distance_legacy(
    distance: float,
    proximity: float,
    components: dict[str, float],
    explanation: list[str],
) -> CareerDistanceResult:
    """Legacy graph-based result with vector fields explicitly cleared."""
    return CareerDistanceResult(
        distance=distance,
        proximity=proximity,
        components=components,
        explanation=explanation,
        semantic_distance=distance,
        dominant_dimensions=[],
        weak_dimensions=[],
        missing_dimensions=[],
        vector_explanation=None,
    )

_SENIORITY_INDEX = {
    SeniorityLevel.INTERN: 0,
    SeniorityLevel.JUNIOR: 1,
    SeniorityLevel.MID: 2,
    SeniorityLevel.SENIOR: 3,
    SeniorityLevel.LEAD: 4,
    SeniorityLevel.PRINCIPAL: 5,
    SeniorityLevel.DIRECTOR: 6,
    SeniorityLevel.VP: 7,
    SeniorityLevel.C_LEVEL: 8,
    SeniorityLevel.UNKNOWN: 3,
}

_LEADERSHIP_INDEX = {
    LeadershipLevel.INDIVIDUAL_CONTRIBUTOR: 0,
    LeadershipLevel.TEAM_LEAD: 1,
    LeadershipLevel.PEOPLE_MANAGER: 2,
    LeadershipLevel.ORG_LEADER: 3,
    LeadershipLevel.EXECUTIVE: 4,
    LeadershipLevel.UNKNOWN: 1,
}

_ENTERPRISE_INDEX = {
    EnterpriseExposure.NONE: 0,
    EnterpriseExposure.LIMITED: 1,
    EnterpriseExposure.MODERATE: 2,
    EnterpriseExposure.STRONG: 3,
    EnterpriseExposure.DEEP: 4,
}

_WEIGHTS = {
    "role_family": 0.35,
    "seniority": 0.15,
    "leadership": 0.15,
    "domain": 0.15,
    "enterprise": 0.10,
    "transformation": 0.10,
}


class CareerDistanceScorer:
    """Compute explainable distance between two career identity vectors."""

    def score(self, inputs: CareerDistanceInput) -> CareerDistanceResult:
        components: dict[str, float] = {}
        explanation: list[str] = []

        rf_dist = self._role_family_distance(
            inputs.source_role_family, inputs.target_role_family
        )
        components["role_family"] = rf_dist
        explanation.append(
            f"Role family: {inputs.source_role_family.value} → "
            f"{inputs.target_role_family.value} (distance {rf_dist:.2f})"
        )

        sen_dist = self._normalized_gap(
            _SENIORITY_INDEX[inputs.source_seniority],
            _SENIORITY_INDEX[inputs.target_seniority],
            max_index=8,
        )
        components["seniority"] = sen_dist
        explanation.append(f"Seniority alignment gap: {sen_dist:.2f}")

        lead_dist = self._normalized_gap(
            _LEADERSHIP_INDEX[inputs.source_leadership],
            _LEADERSHIP_INDEX[inputs.target_leadership],
            max_index=4,
        )
        components["leadership"] = lead_dist
        explanation.append(f"Leadership alignment gap: {lead_dist:.2f}")

        dom_dist = self._domain_distance(
            inputs.source_domains, inputs.target_domains
        )
        components["domain"] = dom_dist
        explanation.append(f"Domain overlap distance: {dom_dist:.2f}")

        ent_dist = self._normalized_gap(
            _ENTERPRISE_INDEX[inputs.source_enterprise],
            _ENTERPRISE_INDEX[inputs.target_enterprise],
            max_index=4,
        )
        components["enterprise"] = ent_dist
        explanation.append(f"Enterprise maturity gap: {ent_dist:.2f}")

        trans_dist = abs(inputs.source_transformation - inputs.target_transformation)
        components["transformation"] = trans_dist
        explanation.append(f"Transformation focus gap: {trans_dist:.2f}")

        distance = sum(components[k] * _WEIGHTS[k] for k in _WEIGHTS)
        distance = round(min(1.0, distance), 3)
        proximity = round(1.0 - distance, 3)

        return _career_distance_legacy(
            distance=distance,
            proximity=proximity,
            components={k: round(v, 3) for k, v in components.items()},
            explanation=explanation,
        )

    def score_profile_to_role_family(
        self,
        profile: CandidateProfile,
        target_role_family: RoleFamilyId,
        *,
        target_seniority: SeniorityLevel | None = None,
        target_leadership: LeadershipLevel | None = None,
        target_domains: list[str] | None = None,
        target_enterprise: EnterpriseExposure | None = None,
        target_transformation: float | None = None,
    ) -> CareerDistanceResult:
        """Convenience: candidate profile vs a hypothetical role-family target."""
        inputs = CareerDistanceInput(
            source_role_family=profile.primary_career_track,
            target_role_family=target_role_family,
            source_seniority=profile.current_seniority,
            target_seniority=target_seniority or profile.current_seniority,
            source_leadership=profile.leadership_level,
            target_leadership=target_leadership or profile.leadership_level,
            source_domains=profile.primary_domains + profile.secondary_domains,
            target_domains=target_domains or profile.primary_domains,
            source_enterprise=profile.enterprise_experience,
            target_enterprise=target_enterprise or profile.enterprise_experience,
            source_transformation=profile.transformation_focus,
            target_transformation=target_transformation
            if target_transformation is not None
            else profile.transformation_focus,
        )
        return self.score(inputs)

    def rank_role_families(
        self, profile: CandidateProfile
    ) -> list[tuple[RoleFamilyId, CareerDistanceResult]]:
        """Rank role families from canonical_ranking snapshot (same as identity ranking)."""
        from career_intelligence_engine.intelligence.role_family_scoring import (
            rank_role_families_from_profile,
            to_career_distance_result,
        )

        ranked = rank_role_families_from_profile(profile)
        return [
            (family_id, to_career_distance_result(result))
            for family_id, result in ranked
        ]

    def rank_role_families_legacy(
        self, profile: CandidateProfile
    ) -> list[tuple[RoleFamilyId, CareerDistanceResult]]:
        """
        Deprecated graph-based ranking (semantic distance only).

        Not used in production — tests only.
        """
        scorer_results: list[tuple[RoleFamilyId, CareerDistanceResult]] = []
        for family_id in ROLE_FAMILIES:
            result = self.score_profile_to_role_family(profile, family_id)
            scorer_results.append((family_id, result))
        return sorted(scorer_results, key=lambda x: x[1].distance)

    def _role_family_distance(
        self, source: RoleFamilyId, target: RoleFamilyId
    ) -> float:
        return compute_family_distance(source, target)

    def _domain_distance(self, source: list[str], target: list[str]) -> float:
        if not source and not target:
            return 0.5
        s = {d.lower() for d in source}
        t = {d.lower() for d in target}
        if not s or not t:
            return 0.6
        overlap = len(s & t)
        union = len(s | t)
        jaccard = overlap / union if union else 0.0
        return round(1.0 - jaccard, 3)

    def _normalized_gap(self, a: int, b: int, max_index: int) -> float:
        if max_index <= 0:
            return 0.0
        return round(abs(a - b) / max_index, 3)
