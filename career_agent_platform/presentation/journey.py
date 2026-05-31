"""Reviewer demo journey — purpose copy and next-step guidance (UI-only)."""

from __future__ import annotations

import streamlit as st

JOURNEY_STEPS: tuple[tuple[str, str, str], ...] = (
    ("overview", "Overview", "Home.py"),
    ("recommendations", "Recommendations", "pages/Job_Recommendations.py"),
    ("market", "Market opportunities", "pages/Market_Opportunities.py"),
    ("workspace", "Application workspace", "pages/Application_Workspace.py"),
    ("cockpit", "Career cockpit", "pages/Application_Dashboard.py"),
)

_STEP_INDEX = {step_id: idx for idx, (step_id, _, _) in enumerate(JOURNEY_STEPS)}


def render_journey_rail(*, active: str) -> None:
    """Compact step indicator below page title — shows where you are in the demo flow."""
    idx = _STEP_INDEX.get(active, 0)
    parts: list[str] = []
    for i, (step_id, label, _) in enumerate(JOURNEY_STEPS):
        if i < idx:
            parts.append(f'<span class="ji-step ji-step-done">{i + 1}. {label}</span>')
        elif i == idx:
            parts.append(f'<span class="ji-step ji-step-active">{i + 1}. {label}</span>')
        else:
            parts.append(f'<span class="ji-step ji-step-todo">{i + 1}. {label}</span>')
    st.markdown(
        f'<nav class="ji-journey-rail" aria-label="Reviewer flow">{" ".join(parts)}</nav>',
        unsafe_allow_html=True,
    )


def render_page_intro(*, active: str, purpose: str) -> None:
    """Standard page header block: journey rail + purpose sentence."""
    render_journey_rail(active=active)
    st.markdown(f'<p class="ji-page-purpose">{purpose}</p>', unsafe_allow_html=True)


def render_next_step(
    *,
    message: str,
    page_path: str,
    button_label: str,
    icon: str = "→",
) -> None:
    """Obvious forward CTA at bottom of a page section."""
    st.markdown('<div class="ji-next-step">', unsafe_allow_html=True)
    c1, c2 = st.columns([2.2, 1])
    with c1:
        st.markdown(f"**Next:** {message}")
    with c2:
        st.page_link(page_path, label=f"{button_label} {icon}", icon=None)
    st.markdown("</div>", unsafe_allow_html=True)


def render_empty_state(
    *,
    title: str,
    body: str,
    steps: list[str] | None = None,
    primary_page: str | None = None,
    primary_label: str = "Go to Recommendations",
) -> None:
    """Structured empty state — clearer than a lone st.info."""
    st.markdown(f'<div class="ji-empty-state"><p class="ji-empty-title">{title}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="ji-empty-body">{body}</p>', unsafe_allow_html=True)
    if steps:
        items = "".join(f"<li>{s}</li>" for s in steps)
        st.markdown(f'<ol class="ji-empty-steps">{items}</ol>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if primary_page:
        st.page_link(primary_page, label=primary_label, icon="🎯")


def render_cockpit_tile(*, label: str, value: str, detail: str = "") -> None:
    """Dense metric tile for Career cockpit — readable without st.metric crowding."""
    tile_style = (
        "border:1px solid rgba(49,51,63,0.1);border-radius:10px;padding:0.7rem 0.85rem;"
        "margin-bottom:0.5rem;background:rgba(255,255,255,0.88);min-height:4.5rem;"
    )
    label_style = (
        "display:block;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.04em;"
        "color:rgba(49,51,63,0.52);font-weight:600;margin:0 0 0.25rem 0;"
    )
    value_style = (
        "display:block;font-size:0.95rem;font-weight:600;color:rgba(49,51,63,0.9);"
        "line-height:1.35;margin:0;"
    )
    detail_style = (
        "display:block;font-size:0.8rem;color:rgba(49,51,63,0.58);margin:0.35rem 0 0 0;"
        "line-height:1.4;"
    )
    detail_html = (
        f'<p class="ji-cockpit-tile-detail" style="{detail_style}">{detail}</p>'
        if detail
        else ""
    )
    st.markdown(
        f'<div class="ji-cockpit-tile" style="{tile_style}">'
        f'<p class="ji-cockpit-tile-label" style="{label_style}">{label}</p>'
        f'<p class="ji-cockpit-tile-value" style="{value_style}">{value}</p>'
        f"{detail_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
