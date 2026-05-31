"""Recruiter-grade recommendation and workspace job cards."""



from __future__ import annotations



import html



import streamlit as st



from job_sources.industry_mapper import industry_chip_label

from job_sources.location_inference import location_display_line

from job_sources.normalization import NormalizedJobPosting, normalized_from_recommendation

from presentation.chips import metric_chips_html, status_chip_html

from presentation.explainability import (

    lines_distinct_from_reference,

    strengths_distinct_from_summary,

    top_n,

)

from presentation.labels import match_category_badge

from presentation.sanitize import format_score_percent, sanitize_bullet_list, sanitize_display_text

from recommendation_engine import RecommendationResult

from resume_routing.router import routing_from_recommendation

from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES

from career_intelligence_engine.models.ontology import RoleFamilyId





def _confidence_badge_label(confidence: float) -> tuple[str, str]:

    if confidence >= 0.72:

        return "High confidence", "success"

    if confidence >= 0.52:

        return "Moderate confidence", "info"

    return "Review confidence", "warning"





def _role_family_chip(role_family: str) -> str:

    try:

        return ROLE_FAMILIES[RoleFamilyId(role_family)].display_name

    except (ValueError, KeyError):

        return role_family.replace("_", " ").title()





def _compact_list_html(items: list[str], *, css_class: str) -> str:

    if not items:

        return ""

    lis = "".join(f"<li>{html.escape(item)}</li>" for item in items)

    return f'<ul class="{css_class}">{lis}</ul>'





def render_entity_header(entity: NormalizedJobPosting, *, match_pct: float, confidence: float, priority_value: str | None) -> None:

    badge = match_category_badge(priority_value)

    conf_label, conf_tone = _confidence_badge_label(confidence)

    loc_line = location_display_line(entity.location, entity.remote_type)

    industry = industry_chip_label(entity.inferred_industry)

    family = _role_family_chip(entity.inferred_role_family)



    chip_html = (

        f'<span class="ji-badge ji-badge-{badge.tone}">{badge.label}</span> '

        f'<span class="ji-badge ji-badge-{conf_tone}">{conf_label}</span> '

        f'<span class="ji-badge ji-badge-muted">{family}</span> '

        f'<span class="ji-badge ji-badge-muted">{industry}</span>'

    )

    st.markdown(chip_html, unsafe_allow_html=True)



    h1, h2 = st.columns([1.35, 1])

    with h1:

        st.markdown(f"### {entity.normalized_title}")

        st.markdown(f"**{entity.company_name}**")

        st.caption(loc_line)

    with h2:

        st.markdown(

            metric_chips_html(

                fit=format_score_percent(match_pct),

                confidence=format_score_percent(confidence),

            ),

            unsafe_allow_html=True,

        )





def render_recruiter_job_card(rec: RecommendationResult) -> None:

    """Compact recommendation card — scan-first hierarchy for recruiter review."""

    entity = normalized_from_recommendation(rec)

    route = routing_from_recommendation(rec)



    st.markdown('<div class="ji-rec-card">', unsafe_allow_html=True)



    render_entity_header(

        entity,

        match_pct=rec.overall_match,

        confidence=rec.confidence,

        priority_value=getattr(rec.recommendation_priority, "value", None),

    )



    brief = sanitize_display_text(rec.recruiter_summary or "")

    if not brief and entity.normalized_summary:

        brief = sanitize_display_text(entity.normalized_summary)



    strengths = sanitize_bullet_list(rec.top_strengths or rec.strengths)[:3]

    gaps = sanitize_bullet_list(rec.gaps or rec.missing_capabilities or rec.missing_dimensions)[:3]

    if not gaps and entity.top_missing_dimensions:

        gaps = entity.top_missing_dimensions[:3]



    if brief:

        strengths = strengths_distinct_from_summary(brief, strengths)



    if not strengths and entity.top_matching_dimensions:

        strengths = entity.top_matching_dimensions[:3]



    reference_for_drivers = [brief, *strengths, *gaps]

    drivers = sanitize_bullet_list(
        lines_distinct_from_reference(reference_for_drivers, top_n(rec.why_matched, 4)),
    )[:2]



    if brief:

        st.markdown(

            f'<p class="ji-rec-brief"><span class="ji-rec-brief-label">Brief</span> '

            f"{html.escape(brief)}</p>",

            unsafe_allow_html=True,

        )

    elif entity.normalized_summary:

        st.markdown(

            f'<p class="ji-rec-summary">{html.escape(entity.normalized_summary)}</p>',

            unsafe_allow_html=True,

        )



    if route and route.recommended_resume:

        st.markdown('<div class="ji-rec-section ji-rec-section-inline">', unsafe_allow_html=True)

        st.markdown(

            f"**Resume** · {html.escape(route.recommended_resume)}"

            + (

                f" — {' · '.join(html.escape(x) for x in route.why_selected[:2])}"

                if route.why_selected

                else ""

            ),

            unsafe_allow_html=True,

        )

        st.markdown("</div>", unsafe_allow_html=True)



    st.markdown('<div class="ji-rec-brief-grid ji-rec-section">', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:

        st.markdown("**Strengths**")

        if strengths:

            st.markdown(

                _compact_list_html(strengths, css_class="ji-rec-list"),

                unsafe_allow_html=True,

            )

        else:

            st.caption("No standout themes highlighted.")

    with c2:

        st.markdown("**Gaps**")

        if gaps:

            st.markdown(

                _compact_list_html(gaps, css_class="ji-rec-list ji-rec-list-gaps"),

                unsafe_allow_html=True,

            )

        else:

            st.caption("No critical gaps flagged.")

    st.markdown("</div>", unsafe_allow_html=True)



    if drivers:

        driver_text = html.escape(" · ".join(drivers))

        st.markdown(

            f'<p class="ji-rec-drivers"><span class="ji-rec-drivers-label">Signals</span> {driver_text}</p>',

            unsafe_allow_html=True,

        )



    st.markdown("</div>", unsafe_allow_html=True)





def render_workspace_job_context(entity: NormalizedJobPosting, *, recommended_resume: str = "") -> None:

    loc_line = location_display_line(entity.location, entity.remote_type)

    st.markdown(f"### {entity.normalized_title}")

    st.markdown(f"**{entity.company_name}** · {industry_chip_label(entity.inferred_industry)}")

    st.caption(f"{loc_line} · {_role_family_chip(entity.inferred_role_family)}")

    if recommended_resume:

        st.info(f"**Recommended resume:** {recommended_resume}")

    if entity.normalized_summary:

        st.write(entity.normalized_summary)

