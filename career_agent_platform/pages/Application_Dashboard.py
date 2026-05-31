"""Career intelligence cockpit — strategic guidance over operational counters."""

from __future__ import annotations

import streamlit as st

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from application_tracking.followup_engine import FollowUpEngine
from application_tracking.tracker import ApplicationTracker
from application_workspace.review_manager import ApplicationReviewManager
from hiring_intelligence.market_opportunities import build_market_snapshot
from job_sources.normalization import pretty_job_label
from presentation.labels import safe_company, safe_title
from presentation.journey import render_cockpit_tile, render_empty_state, render_page_intro
from presentation.nav import render_primary_nav
from presentation.sanitize import format_score_percent
from presentation.sanitize import humanize_gap_line, sanitize_bullet_list
from resume_store.session_manager import get_active_resume
from state_hygiene import (
    get_valid_packages,
    get_valid_tracker_records_for_packages,
    safe_cleanup_demo_state,
)


def _init_session() -> None:
    if "dash_review" not in st.session_state:
        st.session_state.dash_review = ApplicationReviewManager()
        st.session_state.dash_review.initialize()
    if "dash_tracker" not in st.session_state:
        st.session_state.dash_tracker = ApplicationTracker()
        st.session_state.dash_tracker.initialize()
    if "demo_state_cleaned" not in st.session_state:
        safe_cleanup_demo_state()
        st.session_state.demo_state_cleaned = True


render_primary_nav(active="Career cockpit")

st.title("Career cockpit")
render_page_intro(
    active="cockpit",
    purpose=(
        "Executive view: market alignment, skill gaps, recruiter readiness, and application packages "
        "in one place — strategic intelligence without operational clutter."
    ),
)

_init_session()
review_mgr = st.session_state.dash_review
tracker = st.session_state.dash_tracker
followups = FollowUpEngine(tracker).evaluate()
valid_packages = get_valid_packages(review_mgr)
profile = st.session_state.get("career_profile")
active = get_active_resume(st.session_state)

if profile is None and active.resume and active.resume.parsed_profile:
    try:
        profile = CandidateProfile.model_validate(active.resume.parsed_profile)
        st.session_state.career_profile = profile
    except Exception:
        profile = None

st.subheader("Career intelligence snapshot")
if profile is None:
    render_empty_state(
        title="Intelligence unlocks after resume analysis",
        body="Run Recommendations with your resume to populate market alignment, gaps, and strategic guidance here.",
        steps=[
            "Upload a resume and generate ranked matches on Recommendations.",
            "Approve roles you want to pursue.",
            "Return here for a consolidated strategic view.",
        ],
        primary_page="pages/Job_Recommendations.py",
        primary_label="Go to Recommendations",
    )
else:
    snapshot = build_market_snapshot(profile)
    primary_family = (
        snapshot.highest_confidence_role_families[0][0]
        if snapshot.highest_confidence_role_families
        else "—"
    )
    primary_family_score = (
        format_score_percent(snapshot.highest_confidence_role_families[0][1])
        if snapshot.highest_confidence_role_families
        else ""
    )
    top_dims = []
    if active.resume:
        top_dims = list((active.resume.resume_identity or {}).get("dominant_dimensions") or [])[:3]
    best_market = (
        snapshot.best_fit_companies[0].company
        if snapshot.best_fit_companies
        else "—"
    )
    best_market_score = (
        f"{snapshot.best_fit_companies[0].fit_score:.0f}% fit"
        if snapshot.best_fit_companies
        else ""
    )
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        render_cockpit_tile(
            label="Strongest role family",
            value=primary_family,
            detail=primary_family_score,
        )
    with t2:
        render_cockpit_tile(
            label="Dominant dimensions",
            value=", ".join(top_dims) if top_dims else "—",
            detail="From active resume identity",
        )
    with t3:
        render_cockpit_tile(
            label="Best market fit",
            value=best_market,
            detail=best_market_score,
        )
    with t4:
        render_cockpit_tile(
            label="Recruiter readiness",
            value=snapshot.executive_readiness,
            detail=f"AI readiness · {snapshot.ai_readiness}",
        )

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("**Strategic recommendations**")
        for line in snapshot.strategic_recommendations[:4]:
            st.info(line)
        st.markdown("**Top companies for your profile**")
        if snapshot.best_fit_companies:
            for opp in snapshot.best_fit_companies[:5]:
                why = opp.why_fit[0] if opp.why_fit else "Strong alignment"
                st.write(f"- **{opp.company}** ({opp.fit_score:.0f}%) — {why}")
        else:
            st.caption("Company fit appears after profile analysis.")
    with right:
        if active.resume:
            st.markdown("**Active resume**")
            st.markdown(f"**{active.resume.file_name}**")
            st.caption(
                f"{str((active.resume.resume_identity or {}).get('role_family') or '').replace('_', ' ').title()} · "
                f"{(active.resume.resume_identity or {}).get('recommended_resume_label') or ''}",
            )
            skills = (active.resume.resume_identity or {}).get("top_skills") or []
            if skills:
                st.write("Top skills: " + ", ".join(list(skills)[:8]))
        st.markdown("**Best resume variant**")
        if snapshot.resume_variant_performance:
            best = snapshot.resume_variant_performance[0]
            st.write(f"**{best[0]}** — {best[1]:.0f}% role-family alignment")
        else:
            st.caption("Variant scoring requires a saved profile.")
        st.markdown("**Fastest-growing skill gaps**")
        for gap in snapshot.fastest_growing_gaps[:4]:
            st.write(f"- {gap}")
        if snapshot.recommended_upskilling:
            st.markdown("**Suggested upskilling**")
            for item in snapshot.recommended_upskilling[:3]:
                st.write(f"- {item}")

    with st.expander("Skill demand heatmap", expanded=False):
        if snapshot.skill_heatmap:
            st.table([row.to_dict() for row in snapshot.skill_heatmap])
        else:
            st.caption("No skill demand data yet.")

    st.caption(
        f"Hiring alignment · Transformation maturity **{profile.transformation_focus:.0%}** · "
        f"Executive readiness **{snapshot.executive_readiness}**",
    )

st.divider()
st.subheader("Application pipeline")
if len(valid_packages) == 0:
    st.info(
        "No application packages yet. Approve a role on **Recommendations**, "
        "then generate a package in **Application workspace**.",
    )
else:
    st.caption(f"{len(valid_packages)} package(s) in your pipeline")

if followups.pending_followups:
    with st.expander("Follow-up reminders", expanded=False):
        for item in followups.pending_followups[:8]:
            st.write(
                f"**{safe_company(item.company)}** — {safe_title(item.role)}: "
                f"{item.recommended_action} ({item.days_since_last_action} days)",
            )

meaningful = []
for pkg in valid_packages[:12]:
    snap = pkg.recommendation_snapshot or {}
    label = pretty_job_label(
        title=pkg.job_title,
        company=pkg.company,
        normalized=snap.get("normalized"),
    )
    route = (snap.get("resume_routing") or {}).get("recommended_resume", "")
    meaningful.append((label, route, snap))

if meaningful:
    st.subheader("Recent packages")
    for label, route, snap in meaningful:
        with st.expander(label, expanded=False):
            if route:
                st.caption(f"Resume: {route}")
            approved = sanitize_bullet_list(snap.get("why_matched") or [])[:3]
            if approved:
                st.markdown("**Why matched**")
                for w in approved:
                    st.write(f"- {w}")
            gaps = sanitize_bullet_list(snap.get("gaps") or [])[:3]
            if gaps:
                st.markdown("**Gaps**")
                for g in gaps:
                    st.write(f"- {humanize_gap_line(g) or g}")
