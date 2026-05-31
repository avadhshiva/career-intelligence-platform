"""Shared demo-mode banner for Streamlit pages."""

from __future__ import annotations

import streamlit as st

from demo_mode import is_demo_mode


def render_demo_mode_banner() -> None:
    if is_demo_mode():
        st.warning(
            "Demo mode — disk persistence is off for this session. "
            "Resume/JD upload and **Generate ranked recommendations** still work; "
            "restart clears queue and packages.",
            icon="ℹ️",
        )
