"""Phase 5A recommendation engine — deterministic ranking and explainability."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.matching.job_match_engine import JobMatchEngine
from career_intelligence_engine.matching.result import JobMatchResult
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.ontology.capability_vectors import (
    DIMENSION_LABELS,
    dimension_contributions,
)
from job_sources.job_posting import JobPosting


class RecommendationPriority(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    BORDERLINE = "BORDERLINE"
    LOW_MATCH = "LOW_MATCH"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class RecommendationResult:
    """Human-reviewable recommendation with full explainability."""

    job_id: str
    job_title: str
    company: str
    source: str
    overall_match: float
    confidence: float
    eligibility_passed: bool
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recruiter_summary: str = ""
    recommendation_priority: RecommendationPriority = RecommendationPriority.LOW_MATCH
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    rejection_reason: str = ""
    why_matched: list[str] = field(default_factory=list)
    why_not_matched: list[str] = field(default_factory=list)
    top_strengths: list[str] = field(default_factory=list)
    top_risks: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    dominant_dimensions: list[str] = field(default_factory=list)
    missing_dimensions: list[str] = field(default_factory=list)
    match_detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_title": self.job_title,
            "company": self.company,
            "source": self.source,
            "overall_match": self.overall_match,
            "confidence": self.confidence,
            "eligibility_passed": self.eligibility_passed,
            "strengths": list(self.strengths),
            "gaps": list(self.gaps),
            "risks": list(self.risks),
            "recruiter_summary": self.recruiter_summary,
            "recommendation_priority": self.recommendation_priority.value,
            "approval_status": self.approval_status.value,
            "rejection_reason": self.rejection_reason,
            "why_matched": list(self.why_matched),
            "why_not_matched": list(self.why_not_matched),
            "top_strengths": list(self.top_strengths),
            "top_risks": list(self.top_risks),
            "missing_capabilities": list(self.missing_capabilities),
            "dominant_dimensions": list(self.dominant_dimensions),
            "missing_dimensions": list(self.missing_dimensions),
            "match_detail": dict(self.match_detail),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecommendationResult:
        return cls(
            job_id=str(data["job_id"]),
            job_title=str(data.get("job_title", "")),
            company=str(data.get("company", "")),
            source=str(data.get("source", "")),
            overall_match=float(data.get("overall_match", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            eligibility_passed=bool(data.get("eligibility_passed", False)),
            strengths=list(data.get("strengths") or []),
            gaps=list(data.get("gaps") or []),
            risks=list(data.get("risks") or []),
            recruiter_summary=str(data.get("recruiter_summary", "")),
            recommendation_priority=RecommendationPriority(
                data.get("recommendation_priority", RecommendationPriority.LOW_MATCH.value),
            ),
            approval_status=ApprovalStatus(data.get("approval_status", ApprovalStatus.PENDING.value)),
            rejection_reason=str(data.get("rejection_reason", "")),
            why_matched=list(data.get("why_matched") or []),
            why_not_matched=list(data.get("why_not_matched") or []),
            top_strengths=list(data.get("top_strengths") or []),
            top_risks=list(data.get("top_risks") or []),
            missing_capabilities=list(data.get("missing_capabilities") or []),
            dominant_dimensions=list(data.get("dominant_dimensions") or []),
            missing_dimensions=list(data.get("missing_dimensions") or []),
            match_detail=dict(data.get("match_detail") or {}),
        )


# Calibrated tiers — slightly stricter than raw score bands to reduce inflated labels
_STRONG_MATCH_MIN = 0.78
_GOOD_MATCH_MIN = 0.58
_BORDERLINE_MIN = 0.43


def _priority_bucket(score: float, gate_passed: bool) -> RecommendationPriority:
    if not gate_passed:
        if score >= 0.45:
            return RecommendationPriority.BORDERLINE
        return RecommendationPriority.LOW_MATCH
    if score >= _STRONG_MATCH_MIN:
        return RecommendationPriority.STRONG_MATCH
    if score >= _GOOD_MATCH_MIN:
        return RecommendationPriority.GOOD_MATCH
    if score >= _BORDERLINE_MIN:
        return RecommendationPriority.BORDERLINE
    return RecommendationPriority.LOW_MATCH


def _calibrated_priority(
    score: float,
    gate_passed: bool,
    match: JobMatchResult,
    job: JobProfile,
) -> RecommendationPriority:
    """Downgrade priority when sub-fit lenses disagree with headline score."""
    base = _priority_bucket(score, gate_passed)
    if not gate_passed or base == RecommendationPriority.LOW_MATCH:
        return base

    if base == RecommendationPriority.STRONG_MATCH:
        if job.is_ai_transformation and match.transformation_fit < 0.50:
            return RecommendationPriority.GOOD_MATCH
        if job.is_architecture_heavy and match.architecture_fit < 0.45:
            return RecommendationPriority.GOOD_MATCH
        if job.is_operations_heavy and match.eligibility_fit < 0.55:
            return RecommendationPriority.GOOD_MATCH
        if job.is_product_heavy and match.capability_similarity < 0.52:
            return RecommendationPriority.GOOD_MATCH
        if job.is_release_governance_heavy and match.governance_fit < 0.50:
            return RecommendationPriority.GOOD_MATCH

    if base == RecommendationPriority.GOOD_MATCH:
        if job.is_ai_transformation and match.transformation_fit < 0.40:
            return RecommendationPriority.BORDERLINE
        if score < 0.62 and match.capability_similarity < 0.45:
            return RecommendationPriority.BORDERLINE

    return base


def _pick_lens_phrase(job: JobProfile, lens: str, options: tuple[str, ...]) -> str:
    """Deterministic variant picker — varies copy by role without randomness."""
    if not options:
        return ""
    key = f"{lens}:{job.title or ''}:{job.primary_role_family.value}"
    return options[hash(key) % len(options)]


def _fit_lens_labels(match: JobMatchResult, job: JobProfile) -> dict[str, str]:
    """Human-readable fit lenses for explainability (not shown as raw scores in UX)."""
    lenses: dict[str, str] = {}

    if match.governance_fit >= 0.65:
        lenses["governance"] = _pick_lens_phrase(
            job,
            "governance_strong",
            (
                "Governance and steering cadence match role bar",
                "Program governance depth aligns with role accountability",
                "Steering-forum and governance ownership read as credible",
            ),
        )
    elif match.governance_fit < 0.45 and job.is_release_governance_heavy:
        lenses["governance"] = _pick_lens_phrase(
            job,
            "governance_light",
            (
                "Governance evidence lighter than role expects",
                "Steering and governance ownership less visible than role demands",
                "Program governance depth trails this role's accountability bar",
            ),
        )

    if match.transformation_fit >= 0.65:
        lenses["transformation"] = _pick_lens_phrase(
            job,
            "transformation_strong",
            (
                "Transformation narrative credible for scope",
                "Documented transformation outcomes support role scope",
                "Change and transformation ownership land credibly",
            ),
        )
    elif match.transformation_fit < 0.45 and (
        job.is_ai_transformation or job.transformation_type in ("ai", "digital", "operating_model")
    ):
        lenses["transformation"] = _pick_lens_phrase(
            job,
            "transformation_light",
            (
                "Transformation ownership not yet foregrounded",
                "Operating-model change evidence is thinner than role emphasis",
                "Strategic transformation themes are underrepresented in profile",
            ),
        )

    if match.architecture_fit >= 0.60:
        lenses["architecture"] = _pick_lens_phrase(
            job,
            "architecture_strong",
            (
                "Architecture coordination reads as credible",
                "Solution and enterprise architecture alignment appear solid",
                "Technical architecture governance is well represented",
            ),
        )
    elif match.architecture_fit < 0.45 and job.is_architecture_heavy:
        lenses["architecture"] = _pick_lens_phrase(
            job,
            "architecture_light",
            (
                "Architecture depth below architecture-heavy bar",
                "Solution-alignment ownership is lighter than architecture-centric roles expect",
                "Enterprise architecture coordination is not yet a headline theme",
            ),
        )

    if match.capability_similarity >= 0.55:
        lenses["execution"] = _pick_lens_phrase(
            job,
            "execution_strong",
            (
                "Delivery themes track role-critical capabilities",
                "Execution profile aligns with role delivery priorities",
                "Capability mix matches the role's delivery emphasis",
            ),
        )
    elif match.capability_similarity < 0.42:
        lenses["execution"] = _pick_lens_phrase(
            job,
            "execution_light",
            (
                "Capability mix diverges from role emphasis",
                "Documented capabilities skew away from role-critical themes",
                "Delivery profile diverges from this role's priority mix",
            ),
        )

    return lenses


def _explain_line_seen(lines: list[str], candidate: str) -> bool:
    key = candidate.lower().strip()
    if not key:
        return True
    for existing in lines:
        ex = existing.lower().strip()
        if key == ex or key in ex or ex in key:
            return True
        if len(key) >= 28 and key[:28] in ex:
            return True
    return False


def _missing_dimensions(profile: CandidateProfile, job: JobProfile) -> list[str]:
    cand_vec = profile.capability_vector or {}
    job_vec = job.capability_vector or {}
    _, weak = dimension_contributions(cand_vec, job_vec, top_n=8)
    labels: list[str] = []
    for dim, _ in weak[:6]:
        jw = float(job_vec.get(dim, 0.0))
        cv = float(cand_vec.get(dim, 0.0))
        if jw >= 0.20 and cv < 0.25:
            labels.append(DIMENSION_LABELS.get(dim, dim))
    return labels


def _build_explainability(
    profile: CandidateProfile,
    job: JobProfile,
    match: JobMatchResult,
) -> tuple[list[str], list[str], list[str], list[str]]:
    why_matched: list[str] = []
    why_not_matched: list[str] = []

    if match.gate_passed:
        why_matched.append("Meets role-critical eligibility for this role family.")
    else:
        for reason in match.gate_reasons[:4]:
            cleaned = reason.replace("gate failed:", "").strip()
            if cleaned and not _explain_line_seen(why_not_matched, cleaned):
                why_not_matched.append(cleaned)

    for s in match.strengths[:3]:
        if not _explain_line_seen(why_matched, s):
            why_matched.append(s)

    lenses = _fit_lens_labels(match, job)
    execution_lens = lenses.get("execution", "")
    for label in lenses.values():
        negative = any(
            token in label.lower()
            for token in ("gap", "below", "diverges", "lighter", "not yet")
        )
        target = why_not_matched if negative else why_matched
        if not _explain_line_seen(target, label):
            target.append(label)

    if match.capability_similarity >= 0.52:
        fallback = "Profile themes align with role delivery expectations."
        if not _explain_line_seen(why_matched, execution_lens) and not _explain_line_seen(
            why_matched,
            fallback,
        ):
            why_matched.append(fallback)
    elif match.capability_similarity < 0.40:
        diverge = "Documented capabilities diverge from role-critical themes."
        if not _explain_line_seen(why_not_matched, diverge):
            why_not_matched.append(diverge)

    for g in match.gaps[:3]:
        if not _explain_line_seen(why_not_matched, g):
            why_not_matched.append(g)

    if match.overall_match_score < _GOOD_MATCH_MIN:
        shortlist = "Below competitive shortlist bar for this role tier."
        if not _explain_line_seen(why_not_matched, shortlist):
            why_not_matched.append(shortlist)

    top_strengths = list(match.strengths[:3])
    top_risks = list(match.risks[:3])
    return why_matched, why_not_matched, top_strengths, top_risks


class RecommendationEngine:
    """Candidate + jobs → ranked deterministic recommendations."""

    PRIORITY_ORDER = {
        RecommendationPriority.STRONG_MATCH: 0,
        RecommendationPriority.GOOD_MATCH: 1,
        RecommendationPriority.BORDERLINE: 2,
        RecommendationPriority.LOW_MATCH: 3,
    }

    def __init__(self) -> None:
        self._identity = CareerIdentityEngine()
        self._matcher = JobMatchEngine()

    def analyze_resume(self, resume_text: str) -> CandidateProfile:
        return self._identity.analyze_text(resume_text)

    def recommend(
        self,
        profile: CandidateProfile,
        postings: list[JobPosting],
    ) -> list[RecommendationResult]:
        results: list[RecommendationResult] = []
        for posting in postings:
            job_profile = posting.parsed_job_profile
            if job_profile is None:
                job_profile = self._matcher.parse_job(posting.raw_text)
            match = self._matcher.match(profile, job_profile)
            results.append(self._to_recommendation(profile, posting, job_profile, match))
        return self._stable_rank(results)

    def recommend_from_resume(
        self,
        resume_text: str,
        postings: list[JobPosting],
    ) -> tuple[CandidateProfile, list[RecommendationResult]]:
        profile = self.analyze_resume(resume_text)
        return profile, self.recommend(profile, postings)

    def _to_recommendation(
        self,
        profile: CandidateProfile,
        posting: JobPosting,
        job: JobProfile,
        match: JobMatchResult,
    ) -> RecommendationResult:
        why_matched, why_not_matched, top_strengths, top_risks = _build_explainability(
            profile,
            job,
            match,
        )
        missing_dims = _missing_dimensions(profile, job)
        priority = _calibrated_priority(
            match.overall_match_score,
            match.gate_passed,
            match,
            job,
        )

        from evaluation.recommendation_diagnostics import build_recommendation_diagnostics

        match_detail = self._enriched_match_detail(job, match)
        match_detail["fit_lenses"] = _fit_lens_labels(match, job)
        match_detail["diagnostics"] = build_recommendation_diagnostics(profile, job, match)
        match_detail["calibrated_priority"] = priority.value
        if posting.location:
            match_detail["location"] = posting.location

        return RecommendationResult(
            job_id=posting.job_id,
            job_title=posting.title,
            company=posting.company,
            source=posting.source,
            overall_match=match.overall_match_score,
            confidence=match.confidence,
            eligibility_passed=match.gate_passed,
            strengths=list(match.strengths),
            gaps=list(match.gaps),
            risks=list(match.risks),
            recruiter_summary=match.fit_summary,
            recommendation_priority=priority,
            approval_status=ApprovalStatus.PENDING,
            why_matched=why_matched,
            why_not_matched=why_not_matched,
            top_strengths=top_strengths,
            top_risks=top_risks,
            missing_capabilities=list(match.missing_capabilities),
            dominant_dimensions=list(match.dominant_match_dimensions),
            missing_dimensions=missing_dims,
            match_detail=match_detail,
        )

    @staticmethod
    def _enriched_match_detail(job: JobProfile, match: JobMatchResult) -> dict[str, Any]:
        detail = match.to_dict()
        detail.update(
            {
                "primary_role_family": job.primary_role_family.value,
                "is_product_heavy": job.is_product_heavy,
                "is_operations_heavy": job.is_operations_heavy,
                "is_ai_transformation": job.is_ai_transformation,
                "is_release_governance_heavy": job.is_release_governance_heavy,
                "is_architecture_heavy": job.is_architecture_heavy,
            },
        )
        return detail

    def _stable_rank(self, results: list[RecommendationResult]) -> list[RecommendationResult]:
        return sorted(
            results,
            key=lambda r: (
                self.PRIORITY_ORDER[r.recommendation_priority],
                -r.overall_match,
                -r.confidence,
                r.job_id,
            ),
        )
