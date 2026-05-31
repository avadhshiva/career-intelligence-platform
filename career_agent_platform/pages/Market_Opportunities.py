"""Market intelligence — deterministic company and career fit."""

from __future__ import annotations

import streamlit as st

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from hiring_intelligence.market_opportunities import build_market_snapshot
from presentation.demo_banner import render_demo_mode_banner
from presentation.journey import render_empty_state, render_next_step, render_page_intro
from presentation.nav import render_primary_nav
from presentation.sanitize import format_score_percent
from monitoring.ops_log import log_event
from resume_store.session_manager import get_active_resume
from state_hygiene import safe_cleanup_demo_state


def _init_session() -> None:
    if "demo_state_cleaned" not in st.session_state:
        safe_cleanup_demo_state()
        st.session_state.demo_state_cleaned = True


render_primary_nav(active="Market opportunities")

render_demo_mode_banner()

st.title("Market opportunities")
render_page_intro(
    active="market",
    purpose=(
        "Deterministic hiring intelligence: which companies, industries, and role families "
        "align with your saved profile. Uses the same career profile as Recommendations."
    ),
)

_init_session()

profile = st.session_state.get("career_profile")
active = get_active_resume(st.session_state)

if profile is not None:
    log_event("profile_restore", source="session", page="Market_Opportunities")
elif active.resume and active.resume.parsed_profile:
    try:
        profile = CandidateProfile.model_validate(active.resume.parsed_profile)
        st.session_state.career_profile = profile
        log_event(
            "profile_restore",
            source="canonical_disk",
            page="Market_Opportunities",
            resume_id=active.resume_id,
        )
    except Exception as exc:
        profile = None
        log_event(
            "profile_restore_failed",
            source="canonical_disk",
            page="Market_Opportunities",
            resume_id=active.resume_id,
            error_type=type(exc).__name__,
        )
else:
    log_event("profile_restore", source="none", page="Market_Opportunities")

if profile is None:
    steps = [
        "Open **Recommendations** and upload or paste your resume.",
        "Add job descriptions (or use the sample feed) and generate ranked matches.",
        "Return here — market fit, companies, and skill gaps populate from that profile.",
    ]
    if active.resume:
        steps.insert(
            0,
            f"Resume on file (**{active.resume.file_name}**) — generate matches to analyze it.",
        )
    render_empty_state(
        title="Profile not analyzed yet",
        body="Market intelligence needs a career profile from your resume analysis on Recommendations.",
        steps=steps,
        primary_page="pages/Job_Recommendations.py",
        primary_label="Go to Recommendations",
    )
    st.stop()

snapshot = build_market_snapshot(profile)

st.subheader("Career intelligence snapshot")
c1, c2, c3, c4 = st.columns(4)
primary = snapshot.highest_confidence_role_families[0][0] if snapshot.highest_confidence_role_families else "—"
c1.metric("Strongest role family", primary)
dims = profile.explanations.get("primary_career_track", {}).get("display", "—")
c2.metric("Career track", dims)
c3.metric("AI readiness", snapshot.ai_readiness)
c4.metric("Executive readiness", snapshot.executive_readiness)

if active.resume:
    with st.expander("Active resume", expanded=False):
        ident = active.resume.resume_identity or {}
        st.write(ident.get("recommended_resume_label") or active.resume.file_name)
        summary = ident.get("parsed_profile_summary") or ""
        if summary:
            st.caption(summary)

st.divider()
st.subheader("Best-fit companies")
if snapshot.best_fit_companies:
    for opp in snapshot.best_fit_companies[:10]:
        with st.expander(f"{opp.company} — {opp.fit_score:.0f}% fit", expanded=opp == snapshot.best_fit_companies[0]):
            st.markdown(f"**Recommended resume:** {opp.recommended_resume}")
            st.markdown("**Why fit**")
            for line in opp.why_fit:
                st.write(f"- {line}")
            if opp.hiring_signals:
                st.caption(" · ".join(opp.hiring_signals))
            if opp.risks:
                st.markdown("**Risks**")
                for r in opp.risks:
                    st.write(f"- {r}")
else:
    st.caption("No company profiles available.")

st.subheader("Best-fit industries")
if snapshot.best_fit_industries:
    for industry, score in snapshot.best_fit_industries:
        st.write(f"- **{industry}** — {score:.0f}% average fit")
else:
    st.caption("Industry fit will appear after profile analysis.")

st.subheader("Highest-confidence role families")
for family, score in snapshot.highest_confidence_role_families[:6]:
    st.write(f"- **{family}** — {format_score_percent(score) if score <= 1 else f'{score:.0f}%'}")

st.subheader("Resume variants for this market")
for label, perf in snapshot.resume_variant_performance[:6]:
    st.write(f"- **{label}** — {perf:.0f}% role-family alignment")

st.subheader("Market gaps & upskilling")
g1, g2 = st.columns(2)
with g1:
    st.markdown("**Fastest growing gaps**")
    for gap in snapshot.fastest_growing_gaps:
        st.write(f"- {gap}")
with g2:
    st.markdown("**Recommended upskilling**")
    for item in snapshot.recommended_upskilling:
        st.write(f"- {item}")

st.subheader("Skill heatmap")
if snapshot.skill_heatmap:
    st.table([row.to_dict() for row in snapshot.skill_heatmap])
else:
    st.caption("Skill demand data will populate from your profile.")

st.subheader("Strategic career guidance")
for line in snapshot.strategic_recommendations:
    st.info(line)

st.subheader("Hiring momentum (static intelligence)")
for opp in snapshot.best_fit_companies[:6]:
    signal = opp.hiring_signals[0] if opp.hiring_signals else "Hiring momentum: Stable"
    st.caption(f"{opp.company}: {signal}")

st.divider()
render_next_step(
    message="Turn an approved role into a tailored application package.",
    page_path="pages/Application_Workspace.py",
    button_label="Application workspace",
)
