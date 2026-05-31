"""Market Intelligence MVP — curated feed and deterministic scoring."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from recommendation_engine import RecommendationEngine, RecommendationPriority
from services.market_intelligence_service import MarketIntelligenceService

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
_MARKET_FEED = _PLATFORM_ROOT / "data" / "market_feed.json"


@pytest.fixture
def market_service() -> MarketIntelligenceService:
    return MarketIntelligenceService(engine=RecommendationEngine())


def test_market_feed_loads_opportunities(market_service: MarketIntelligenceService) -> None:
    records = market_service.load_feed_records(_MARKET_FEED)
    assert len(records) >= 18
    locations = {r["location"] for r in records}
    for hub in ("Bengaluru", "Hyderabad", "Chennai", "Pune", "Coimbatore", "Remote"):
        assert hub in locations


def test_scoring_is_deterministic(market_service: MarketIntelligenceService) -> None:
    engine = market_service._engine
    profile = engine.analyze_resume(RESUME_TPM)
    run1 = market_service.score_opportunities(profile)
    run2 = market_service.score_opportunities(profile)
    assert [s.opportunity.job_id for s in run1] == [s.opportunity.job_id for s in run2]
    assert [s.estimated_fit for s in run1] == [s.estimated_fit for s in run2]


def test_report_groups_by_location(market_service: MarketIntelligenceService) -> None:
    profile = market_service._engine.analyze_resume(RESUME_TPM)
    report = market_service.build_report(profile, feed_path=_MARKET_FEED)
    assert report.total_opportunities == len(market_service.load_feed_records(_MARKET_FEED))
    assert "Bengaluru" in report.by_location
    assert report.top_companies
    assert "curated" in report.disclaimer.lower() or "sample" in report.disclaimer.lower()


def test_concise_rationale_dedupes(market_service: MarketIntelligenceService) -> None:
    profile = market_service._engine.analyze_resume(RESUME_TPM)
    scored = market_service.score_opportunities(profile)
    assert scored
    bullets = market_service.concise_rationale(scored[0].recommendation, max_items=3)
    assert 1 <= len(bullets) <= 3
    assert len({b.lower()[:40] for b in bullets}) == len(bullets)


def test_tpm_resume_finds_strong_tpm_matches(market_service: MarketIntelligenceService) -> None:
    profile = market_service._engine.analyze_resume(RESUME_TPM)
    scored = market_service.score_opportunities(profile)
    tpm_roles = [s for s in scored if "tpm" in s.opportunity.job_id.lower() or "program" in s.opportunity.role.lower()]
    assert tpm_roles
    top = tpm_roles[0]
    assert top.recommendation.recommendation_priority in (
        RecommendationPriority.STRONG_MATCH,
        RecommendationPriority.GOOD_MATCH,
        RecommendationPriority.BORDERLINE,
    )
