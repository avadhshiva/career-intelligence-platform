"""Executive summary hero — low cognitive load, above-the-fold brief."""

from __future__ import annotations

import streamlit as st

from application_workspace.models import ApplicationPackage
from presentation.explainability import (
    build_executive_summary,
    humanize_dimensions,
    strengths_distinct_from_summary,
    top_n,
    uniq,
)
from presentation.chips import metric_chips_html, role_subline_html, status_chip_html
from presentation.labels import format_location, match_category_badge, safe_company, safe_title
from presentation.sanitize import (
    format_score_percent,
    humanize_gap_line,
    resolve_snapshot_scores,
    sanitize_bullet_list,
    sanitize_display_text,
)
from presentation.job_card import render_recruiter_job_card
from recommendation_engine import RecommendationResult

def _role_location_from_rec(rec: RecommendationResult) -> str:
    detail = rec.match_detail or {}
    return format_location(str(detail.get("location") or detail.get("job_location") or ""))


def render_recommendation_hero(rec: RecommendationResult) -> None:
    """Recruiter-grade recommendation card (entity layer)."""
    render_recruiter_job_card(rec)


def render_recommendation_details(rec: RecommendationResult) -> None:
    """Advanced explainability — keep collapsed by default."""
    with st.expander("Details (explainability)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Why matched**")
            for item in uniq(rec.why_matched)[:6]:
                st.write(f"- {item}")
            if not uniq(rec.why_matched):
                st.caption("—")
            st.markdown("**Dominant dimensions**")
            dims = humanize_dimensions(rec.dominant_dimensions)
            st.write(", ".join(dims) if dims else "—")
        with c2:
            st.markdown("**Why not matched**")
            for item in uniq(rec.why_not_matched)[:6]:
                st.write(f"- {item}")
            if not uniq(rec.why_not_matched):
                st.caption("—")
            st.markdown("**Missing dimensions**")
            miss = humanize_dimensions(rec.missing_dimensions)
            st.write(", ".join(miss) if miss else "—")

        if rec.missing_capabilities:
            st.markdown("**Missing capabilities**")
            for item in top_n(rec.missing_capabilities, 6):
                st.write(f"- {item}")

        diagnostics = (rec.match_detail or {}).get("diagnostics") or {}
        if diagnostics:
            with st.expander("Diagnostics (governance)", expanded=False):
                adj = diagnostics.get("adjacency") or {}
                if adj.get("reasoning"):
                    st.markdown("**Adjacency reasoning**")
                    for line in adj["reasoning"][:4]:
                        st.write(f"- {line}")
                clusters = diagnostics.get("matched_role_clusters") or []
                if clusters:
                    st.markdown("**Role clusters**")
                    st.write(", ".join(clusters))
                top_dims = diagnostics.get("top_matching_dimensions") or []
                if top_dims:
                    st.markdown("**Top matching dimensions**")
                    st.write(", ".join(humanize_dimensions(top_dims)))

        with st.expander("Raw match detail (JSON)", expanded=False):
            st.json(rec.match_detail)


def render_workspace_hero(pkg: ApplicationPackage, *, state_badge: str) -> None:
    """Executive brief for an application package — above lifecycle actions."""
    snap = pkg.recommendation_snapshot or {}
    rec_badge = match_category_badge(str(snap.get("recommendation_priority") or ""))
    resume_alignment = pkg.quality_scores.resume_alignment if pkg.quality_scores else None
    fit_label, conf_label = resolve_snapshot_scores(
        snap,
        package_confidence=pkg.confidence,
        resume_alignment=resume_alignment,
    )
    pkg_conf_label = format_score_percent(pkg.confidence)

    strengths_all = sanitize_bullet_list(
        (pkg.interview_prep.strongest_strengths if pkg.interview_prep else []),
    )[:3]
    gaps = sanitize_bullet_list(
        (pkg.interview_prep.risk_areas if pkg.interview_prep else []),
    )[:3]
    positioning = build_executive_summary(
        recruiter_summary=sanitize_display_text(str(snap.get("recruiter_summary") or "")) or None,
        strengths=strengths_all,
        gaps=[humanize_gap_line(g) or g for g in gaps],
        risks=[humanize_gap_line(g) or g for g in gaps],
    )
    strengths = strengths_distinct_from_summary(positioning, strengths_all)

    st.markdown(status_chip_html(rec_badge), unsafe_allow_html=True)
    st.caption(f"Lifecycle {state_badge}")
    h1, h2 = st.columns([1.35, 1])
    with h1:
        st.markdown(f"### {safe_title(pkg.job_title)}")
        st.markdown(
            role_subline_html(
                safe_company(pkg.company),
                "",
                f"{rec_badge.label} · Package {pkg_conf_label}",
            ),
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(metric_chips_html(fit=fit_label, confidence=conf_label), unsafe_allow_html=True)

    st.markdown("**Positioning**")
    st.write(positioning)

    st.divider()

    s1, s2 = st.columns(2)
    with s1:
        st.markdown("**Top strengths**")
        for item in strengths:
            st.write(f"- {item}")
        if not strengths:
            if strengths_all:
                st.caption("Covered in positioning above.")
            else:
                st.caption("None highlighted.")
    with s2:
        st.markdown("**Main gaps**")
        for item in gaps:
            st.write(f"- {item}")
        if not gaps:
            st.caption("None highlighted.")

