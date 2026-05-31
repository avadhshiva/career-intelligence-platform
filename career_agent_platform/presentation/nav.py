from __future__ import annotations

import streamlit as st

from presentation.theme import inject_global_styles


def render_primary_nav(*, active: str | None = None) -> None:
    """Render a stable, simplified navigation in the sidebar.

    Safe: UI-only links; does not alter any engine/session logic.
    """
    inject_global_styles()

    with st.sidebar:
        st.markdown("### Navigate")

        st.page_link("Home.py", label="Overview", icon="🏠")
        st.page_link("pages/Job_Recommendations.py", label="Recommendations", icon="🎯")
        st.page_link("pages/Market_Opportunities.py", label="Market opportunities", icon="🌐")
        st.page_link("pages/Application_Workspace.py", label="Application workspace", icon="🧰")
        st.page_link("pages/Application_Dashboard.py", label="Career cockpit", icon="📈")

        st.divider()

        if active:
            st.markdown(
                f'<p style="font-size:0.8rem;color:rgba(49,51,63,0.55);margin:0;">'
                f"Active · <strong style=\"color:rgba(49,51,63,0.85);\">{active}</strong></p>",
                unsafe_allow_html=True,
            )

