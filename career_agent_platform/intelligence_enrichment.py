"""Enrich recommendations for UX without changing match scores."""

from __future__ import annotations

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from job_sources.job_posting import JobPosting
from job_sources.normalization import apply_normalization_to_recommendation, persist_entity_snapshot
from recommendation_engine import RecommendationResult
from resume_routing.router import attach_routing_to_recommendation


def enrich_recommendations(
    profile: CandidateProfile,
    recommendations: list[RecommendationResult],
    postings: list[JobPosting],
    *,
    active_resume_label: str | None = None,
) -> list[RecommendationResult]:
    """Apply normalization + resume routing to each recommendation."""
    posting_by_id = {p.job_id: p for p in postings}
    for rec in recommendations:
        posting = posting_by_id.get(rec.job_id)
        raw = posting.raw_text if posting else ""
        entity = apply_normalization_to_recommendation(rec, raw_text=raw, posting=posting)
        detail = dict(rec.match_detail or {})
        detail["job_entity"] = persist_entity_snapshot(entity)
        rec.match_detail = detail
        attach_routing_to_recommendation(
            profile=profile,
            rec=rec,
            active_resume_label=active_resume_label,
        )
    return recommendations
