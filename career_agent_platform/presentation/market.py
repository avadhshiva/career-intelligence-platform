"""Market Intelligence tab — compact, executive-style opportunity cards."""

from __future__ import annotations

import streamlit as st

from presentation.chips import metric_chips_html, status_chip_html
from presentation.labels import match_category_badge, safe_company, safe_title
from presentation.sanitize import format_score_percent
from services.market_intelligence_service import (
    CompanyHiringSignal,
    MarketIntelligenceReport,
    ScoredOpportunity,
)
from services.market_intelligence_service import MarketIntelligenceService


def render_market_intelligence_tab(
    *,
    profile,
    service: MarketIntelligenceService,
) -> None:
    """Curated feed + estimated fit — requires analyzed resume profile."""
    st.caption(
        "Sample curated market feed · Estimated fit from your resume · "
        "Not live job listings or automated applications.",
    )

    report = service.build_report(profile)

    st.markdown(f"**{report.feed_description}**")
    st.caption(report.disclaimer)

    if report.total_opportunities == 0:
        st.info("No curated opportunities in the feed.")
        return

    _render_top_companies(report.top_companies)
    st.divider()

    for location, items in report.by_location.items():
        st.markdown(f"#### {location}")
        st.caption(f"{len(items)} curated roles · ranked by estimated fit")
        for scored in items:
            _render_opportunity_card(scored, service)
        st.markdown("")


def _render_top_companies(signals: list[CompanyHiringSignal]) -> None:
    st.markdown("#### Top hiring companies")
    if not signals:
        st.caption("No company signals yet.")
        return
    cols = st.columns(min(4, len(signals)))
    for idx, signal in enumerate(signals[:4]):
        with cols[idx % len(cols)]:
            fit_pct = format_score_percent(signal.avg_fit)
            st.markdown(
                f'<div class="ji-opp-card">'
                f'<p class="ji-opp-title">{safe_company(signal.company)}</p>'
                f'<p class="ji-opp-meta">{signal.opportunity_count} roles · '
                f"avg fit {fit_pct} · {signal.top_location}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_opportunity_card(
    scored: ScoredOpportunity,
    service: MarketIntelligenceService,
) -> None:
    rec = scored.recommendation
    opp = scored.opportunity
    badge = match_category_badge(getattr(rec.recommendation_priority, "value", None))
    fit_label = format_score_percent(rec.overall_match)
    conf_label = format_score_percent(rec.confidence)
    rationale = service.concise_rationale(rec)
    salary = opp.salary_range or ""
    meta_parts = [safe_company(opp.company), opp.location]
    if salary:
        meta_parts.append(salary)
    meta_line = " • ".join(meta_parts)

    rationale_html = "".join(f"<li>{line}</li>" for line in rationale)
    if not rationale_html:
        rationale_html = "<li>Review positioning in ranked matches for detail.</li>"

    st.markdown(
        f'<div class="ji-opp-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.75rem;flex-wrap:wrap;">'
        f"<div style=\"flex:1;min-width:12rem;\">"
        f"{status_chip_html(badge)}"
        f'<p class="ji-opp-title">{safe_title(opp.role)}</p>'
        f'<p class="ji-opp-meta">{meta_line}</p>'
        f"</div>"
        f"{metric_chips_html(fit=fit_label, confidence=conf_label)}"
        f"</div>"
        f"<p style=\"font-size:0.82rem;color:rgba(49,51,63,0.72);margin:0 0 0.35rem 0;\">"
        f"{opp.jd_summary}</p>"
        f'<ul class="ji-rationale">{rationale_html}</ul>'
        f"</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.caption(f"Suggested priority · **{scored.priority_label}**")
    with c2:
        if opp.job_url:
            st.link_button("Search on LinkedIn", opp.job_url, use_container_width=True)
        else:
            st.button("Search on LinkedIn", disabled=True, use_container_width=True)
            st.caption("Listing unavailable")
