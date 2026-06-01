"""Career Agent Platform — Streamlit multipage home."""

import streamlit as st

from monitoring.ops_log import configure_ops_logging, log_event
from presentation.demo_banner import render_demo_mode_banner
from presentation.journey import render_next_step, render_page_intro
from presentation.nav import render_primary_nav
from version import BUILD_INFO, DETERMINISM_NOTE, __version__

configure_ops_logging()
log_event(
    "app_startup",
    page="Home",
    version=__version__,
    release=BUILD_INFO["release"],
    deterministic=BUILD_INFO["deterministic"],
)

st.set_page_config(
    page_title="Career Agent Platform",
    page_icon="🎯",
    layout="wide",
)

render_primary_nav(active="Overview")

render_demo_mode_banner()

st.title("Career Agent Platform (Beta)")

st.info(
    """
🚀 **Public Beta**

Upload your resume and explore AI-assisted career recommendations.

This platform is under active development. Recommendations are intended as
career guidance and may evolve as the scoring models improve.

Your feedback is highly appreciated and will directly influence future releases.
"""
)

render_page_intro(
    active="overview",
    purpose=(
        "Internal career intelligence workflow: rank roles against your resume, approve targets, "
        "build application packages, and monitor market alignment — each step stays human-approved."
    ),
)

st.markdown(
    """
**Demo flow (about 10 minutes)**

1. **Recommendations** — upload a resume, generate ranked roles, read each brief, approve 2+ strong fits.
2. **Market opportunities** — see which companies and role families align with your profile.
3. **Application workspace** — generate resume, cover letter, and prep for an approved role.
4. **Career cockpit** — strategic summary, packages in progress, and follow-up reminders.
"""
)

render_next_step(
    message="Start by generating ranked matches from your resume.",
    page_path="pages/Job_Recommendations.py",
    button_label="Open Recommendations",
)

st.divider()

st.subheader("📝 Feedback")

st.write(
    "This beta release improves through real user feedback. "
    "If you find bugs, inaccurate recommendations, usability issues, or have ideas "
    "for improvement, please share your feedback."
)

st.link_button(
    "Submit Feedback",
    "https://docs.google.com/forms/d/e/1FAIpQLSeXL2lioYbVJDKIekALJw_kXDy9_HQDLZ7D-W3d6vhbUWAVdg/viewform?usp=publish-editor"
)

st.caption(
    f"Version {__version__} · Deterministic matching · "
    "You approve every step · No auto-apply or browser automation."
)

with st.expander("Engineering notes", expanded=False):
    st.markdown(DETERMINISM_NOTE)
    st.caption(BUILD_INFO["benchmark_status"])