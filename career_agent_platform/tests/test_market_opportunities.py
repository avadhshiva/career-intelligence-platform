"""Market intelligence snapshot."""

from __future__ import annotations

from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from hiring_intelligence.market_opportunities import build_market_snapshot, build_skill_heatmap
from hiring_intelligence.opportunity_ranker import rank_company_opportunities
from recommendation_engine import RecommendationEngine


def test_rank_company_opportunities() -> None:
    engine = RecommendationEngine()
    profile = engine.analyze_resume(RESUME_TPM)
    ranked = rank_company_opportunities(profile)
    assert len(ranked) >= 10
    assert ranked[0].fit_score > 0
    assert ranked[0].company
    assert ranked[0].recommended_resume


def test_build_market_snapshot() -> None:
    engine = RecommendationEngine()
    profile = engine.analyze_resume(RESUME_TPM)
    snap = build_market_snapshot(profile)
    assert snap.best_fit_companies
    assert snap.strategic_recommendations
    assert snap.skill_heatmap
    assert snap.ai_readiness


def test_skill_heatmap_rows() -> None:
    engine = RecommendationEngine()
    profile = engine.analyze_resume(RESUME_TPM)
    rows = build_skill_heatmap(profile)
    assert rows[0].skill
    assert rows[0].market_demand in {"High", "Medium", "Very High"}
