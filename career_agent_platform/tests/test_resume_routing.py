"""Resume variant routing."""

from __future__ import annotations

from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from career_intelligence_engine.tests.fixtures.sample_jds import JD_TPM
from job_sources.generic_job_parser import GenericJobParser
from intelligence_enrichment import enrich_recommendations
from recommendation_engine import RecommendationEngine
from resume_routing.router import RESUME_VARIANTS, route_resume, route_resume_for_family
from resume_routing.explanations import attach_routing_to_recommendation


def test_route_tpm_job_to_tpm_variant() -> None:
    engine = RecommendationEngine()
    parser = GenericJobParser()
    posting = parser.parse_pasted_text(JD_TPM, job_id="tpm1", title="TPM", company="Global Tech")
    profile, recs = engine.recommend_from_resume(RESUME_TPM, [posting])
    enrich_recommendations(profile, recs, [posting])
    rec = recs[0]
    route = rec.match_detail.get("resume_routing") or {}
    assert route.get("recommended_resume")
    assert route.get("why_selected")
    assert route.get("confidence", 0) > 0


def test_route_resume_for_family() -> None:
    engine = RecommendationEngine()
    profile = engine.analyze_resume(RESUME_TPM)
    label = route_resume_for_family(profile, "release_governance")
    assert "Governance" in label or "Release" in label


def test_routing_attaches_explanations() -> None:
    engine = RecommendationEngine()
    profile = engine.analyze_resume("Operations manager\nSLA management\nIncident response")
    parser = GenericJobParser()
    posting = parser.parse_pasted_text(
        "Operations lead for run-state service management at Target.",
        job_id="ops1",
        title="Operations Manager",
        company="Target",
    )
    recs = engine.recommend(profile, [posting])
    rec = recs[0]
    attach_routing_to_recommendation(profile=profile, rec=rec)
    route = rec.match_detail["resume_routing"]
    assert route["recommended_resume"]
    assert len(route["why_selected"]) >= 1
