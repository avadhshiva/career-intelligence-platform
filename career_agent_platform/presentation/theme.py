"""Light global styling — typography, cards, chips, sidebar. UI-only."""

from __future__ import annotations

import streamlit as st

_THEME_CSS = """
<style>
/* Typography rhythm */
[data-testid="stAppViewContainer"] h1 {
  font-weight: 600;
  letter-spacing: -0.02em;
  margin-bottom: 0.25rem;
}
[data-testid="stAppViewContainer"] h3 {
  font-weight: 600;
  letter-spacing: -0.01em;
  margin-bottom: 0.15rem;
}
[data-testid="stCaptionContainer"] p {
  color: rgba(49, 51, 63, 0.62);
  font-size: 0.85rem;
  line-height: 1.45;
}

/* Softer expander / card surfaces */
[data-testid="stExpander"] details {
  border: 1px solid rgba(49, 51, 63, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}
[data-testid="stExpander"] summary {
  padding: 0.65rem 0.85rem;
  font-weight: 500;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
  padding: 0.35rem 0.85rem 0.85rem;
  border-top: 1px solid rgba(49, 51, 63, 0.08);
}

/* Compact metric chips (hero) */
.ji-metrics {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  flex-wrap: wrap;
  margin-top: 0.15rem;
}
.ji-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.12rem;
  padding: 0.4rem 0.7rem;
  border-radius: 8px;
  border: 1px solid rgba(49, 51, 63, 0.1);
  background: rgba(248, 250, 252, 0.9);
  min-width: 5rem;
}
.ji-metric-label {
  display: block;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgba(49, 51, 63, 0.55);
  font-weight: 500;
  line-height: 1.15;
  white-space: nowrap;
}
.ji-metric-value {
  display: block;
  font-size: 1rem;
  font-weight: 600;
  color: rgba(49, 51, 63, 0.92);
  line-height: 1.25;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
@media (max-width: 640px) {
  .ji-metrics {
    justify-content: flex-start;
    width: 100%;
  }
  .ji-metric {
    flex: 1 1 5.5rem;
    min-width: 4.75rem;
  }
}

/* Semantic status chips */
.ji-badge {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
  margin-bottom: 0.35rem;
}
.ji-badge-success {
  color: #0d6832;
  background: #e8f5ee;
  border-color: #b8e0c8;
}
.ji-badge-info {
  color: #1a4d8c;
  background: #e8f1fb;
  border-color: #c5d9f5;
}
.ji-badge-warning {
  color: #8a5a00;
  background: #fff6e5;
  border-color: #f0d9a8;
}
.ji-badge-muted {
  color: rgba(49, 51, 63, 0.65);
  background: rgba(248, 250, 252, 0.95);
  border-color: rgba(49, 51, 63, 0.12);
}

/* Role header block */
.ji-role-header {
  margin-bottom: 0.35rem;
}
.ji-role-subline {
  font-size: 0.85rem;
  color: rgba(49, 51, 63, 0.62);
  margin: 0.1rem 0 0.5rem 0;
  line-height: 1.4;
}

/* Market opportunity cards */
.ji-opp-card {
  border: 1px solid rgba(49, 51, 63, 0.1);
  border-radius: 10px;
  padding: 0.75rem 0.9rem;
  margin-bottom: 0.55rem;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}
.ji-opp-title {
  font-weight: 600;
  font-size: 0.95rem;
  margin: 0 0 0.2rem 0;
  color: rgba(49, 51, 63, 0.92);
}
.ji-opp-meta {
  font-size: 0.8rem;
  color: rgba(49, 51, 63, 0.58);
  margin-bottom: 0.45rem;
}
.ji-rationale {
  font-size: 0.82rem;
  color: rgba(49, 51, 63, 0.75);
  margin: 0.35rem 0 0.25rem 0;
  padding-left: 0;
  list-style: none;
}
.ji-rationale li {
  margin: 0.15rem 0;
  padding-left: 0.85rem;
  position: relative;
}
.ji-rationale li::before {
  content: "·";
  position: absolute;
  left: 0;
  color: rgba(49, 51, 63, 0.35);
}

/* Sidebar spacing & active cue */
[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
  padding-top: 0.25rem;
}
[data-testid="stSidebar"] a {
  border-radius: 8px;
  padding: 0.15rem 0.35rem;
}
[data-testid="stSidebar"] .stMarkdown h3 {
  font-size: 0.95rem;
  margin-bottom: 0.35rem;
}

/* Reviewer journey rail */
.ji-journey-rail {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.5rem;
  margin: 0.35rem 0 0.65rem 0;
  padding: 0.45rem 0.55rem;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(49, 51, 63, 0.08);
}
.ji-step {
  font-size: 0.72rem;
  padding: 0.15rem 0.45rem;
  border-radius: 6px;
  white-space: nowrap;
}
.ji-step-active {
  font-weight: 600;
  color: rgba(26, 77, 140, 0.95);
  background: #e8f1fb;
  border: 1px solid #c5d9f5;
}
.ji-step-done {
  color: rgba(13, 104, 50, 0.85);
}
.ji-step-todo {
  color: rgba(49, 51, 63, 0.45);
}

.ji-page-purpose {
  font-size: 0.9rem;
  line-height: 1.48;
  color: rgba(49, 51, 63, 0.72);
  margin: 0 0 0.65rem 0;
  max-width: 52rem;
}

/* Main content vertical rhythm */
[data-testid="stAppViewContainer"] .block-container {
  padding-top: 1.25rem;
  padding-bottom: 2rem;
}
[data-testid="stAppViewContainer"] hr {
  margin: 0.65rem 0;
}

/* Recommendation card interior */
.ji-rec-card {
  padding: 0.1rem 0 0.25rem 0;
}
.ji-rec-section {
  margin: 0.45rem 0 0.35rem 0;
  padding-top: 0.45rem;
  border-top: 1px solid rgba(49, 51, 63, 0.08);
}
.ji-rec-section-inline {
  border-top: none;
  padding-top: 0.15rem;
  margin-top: 0.35rem;
  font-size: 0.84rem;
  color: rgba(49, 51, 63, 0.78);
}
.ji-rec-section:first-of-type {
  border-top: none;
  padding-top: 0;
  margin-top: 0.2rem;
}
.ji-rec-brief {
  font-size: 0.9rem;
  line-height: 1.5;
  color: rgba(49, 51, 63, 0.86);
  margin: 0.4rem 0 0.2rem 0;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(49, 51, 63, 0.08);
}
.ji-rec-brief-label,
.ji-rec-drivers-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 600;
  color: rgba(49, 51, 63, 0.48);
  margin-right: 0.35rem;
}
.ji-rec-summary {
  font-size: 0.88rem;
  line-height: 1.5;
  color: rgba(49, 51, 63, 0.82);
  margin: 0.3rem 0 0.2rem 0;
}
.ji-rec-brief-grid {
  margin-top: 0.35rem !important;
}
.ji-rec-list {
  margin: 0.2rem 0 0 0;
  padding: 0 0 0 1rem;
  font-size: 0.84rem;
  line-height: 1.45;
  color: rgba(49, 51, 63, 0.82);
}
.ji-rec-list li {
  margin: 0.12rem 0;
}
.ji-rec-list-gaps li {
  color: rgba(49, 51, 63, 0.72);
}
.ji-rec-drivers {
  font-size: 0.8rem;
  color: rgba(49, 51, 63, 0.58);
  margin-top: 0.3rem;
  line-height: 1.45;
}

/* Empty states & next-step band */
.ji-empty-state {
  border: 1px dashed rgba(49, 51, 63, 0.18);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  margin: 0.5rem 0 0.75rem 0;
  background: rgba(248, 250, 252, 0.6);
}
.ji-empty-title {
  font-weight: 600;
  font-size: 0.95rem;
  margin: 0 0 0.35rem 0;
  color: rgba(49, 51, 63, 0.9);
}
.ji-empty-body {
  font-size: 0.88rem;
  line-height: 1.5;
  margin: 0 0 0.5rem 0;
  color: rgba(49, 51, 63, 0.68);
}
.ji-empty-steps {
  margin: 0.25rem 0 0 1.1rem;
  padding: 0;
  font-size: 0.85rem;
  line-height: 1.55;
  color: rgba(49, 51, 63, 0.75);
}
.ji-next-step {
  margin-top: 0.75rem;
  padding: 0.75rem 0.85rem;
  border-radius: 10px;
  border: 1px solid rgba(26, 77, 140, 0.15);
  background: rgba(232, 241, 251, 0.45);
}

/* Cockpit summary tiles */
.ji-cockpit-tile {
  border: 1px solid rgba(49, 51, 63, 0.1);
  border-radius: 10px;
  padding: 0.7rem 0.85rem;
  margin-bottom: 0.5rem;
  background: rgba(255, 255, 255, 0.88);
  min-height: 4.5rem;
}
.ji-cockpit-tile-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgba(49, 51, 63, 0.52);
  font-weight: 600;
  margin: 0 0 0.25rem 0;
}
.ji-cockpit-tile-value {
  font-size: 0.95rem;
  font-weight: 600;
  color: rgba(49, 51, 63, 0.9);
  line-height: 1.35;
  margin: 0;
}
.ji-cockpit-tile-detail {
  font-size: 0.8rem;
  color: rgba(49, 51, 63, 0.58);
  margin: 0.35rem 0 0 0;
  line-height: 1.4;
}

/* Recommendations matching lifecycle (engine room) */
.ji-pipeline-rail {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.35rem;
  margin: 0.25rem 0 0.45rem 0;
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(49, 51, 63, 0.1);
}
.ji-pipe-arrow {
  font-size: 0.65rem;
  color: rgba(49, 51, 63, 0.28);
  padding: 0 0.05rem;
}
.ji-pipe-stage {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
  white-space: nowrap;
  border: 1px solid transparent;
}
.ji-pipe-done {
  color: rgba(13, 104, 50, 0.88);
  background: rgba(232, 245, 238, 0.7);
  border-color: rgba(184, 224, 200, 0.6);
}
.ji-pipe-active {
  font-weight: 600;
  color: rgba(26, 77, 140, 0.95);
  background: #e8f1fb;
  border-color: #c5d9f5;
}
.ji-pipe-todo {
  color: rgba(49, 51, 63, 0.42);
  background: rgba(248, 250, 252, 0.5);
}

/* Dark theme — metric chips and cards remain legible */
@media (prefers-color-scheme: dark) {
  .ji-metric {
    background: rgba(38, 39, 48, 0.95);
    border-color: rgba(250, 250, 250, 0.12);
  }
  .ji-metric-label { color: rgba(250, 250, 250, 0.55); }
  .ji-metric-value { color: rgba(250, 250, 250, 0.92); }
  .ji-rec-brief {
    background: rgba(38, 39, 48, 0.6);
    border-color: rgba(250, 250, 250, 0.1);
    color: rgba(250, 250, 250, 0.88);
  }
  .ji-rec-list { color: rgba(250, 250, 250, 0.82); }
  .ji-opp-card {
    background: rgba(38, 39, 48, 0.85);
    border-color: rgba(250, 250, 250, 0.1);
  }
}
[data-theme="dark"] .ji-metric,
.stApp[data-theme="dark"] .ji-metric {
  background: rgba(38, 39, 48, 0.95);
  border-color: rgba(250, 250, 250, 0.12);
}
[data-theme="dark"] .ji-metric-label,
.stApp[data-theme="dark"] .ji-metric-label {
  color: rgba(250, 250, 250, 0.55);
}
[data-theme="dark"] .ji-metric-value,
.stApp[data-theme="dark"] .ji-metric-value {
  color: rgba(250, 250, 250, 0.92);
}
[data-theme="dark"] .ji-rec-brief,
.stApp[data-theme="dark"] .ji-rec-brief {
  background: rgba(38, 39, 48, 0.6);
  border-color: rgba(250, 250, 250, 0.1);
  color: rgba(250, 250, 250, 0.88);
}
</style>
"""


_THEME_VERSION = "reviewer-ux-4"


def inject_global_styles() -> None:
    """Apply once per session (versioned) — presentation-only."""
    if st.session_state.get("_ji_theme_version") == _THEME_VERSION:
        return
    st.markdown(_THEME_CSS, unsafe_allow_html=True)
    st.session_state["_ji_theme_version"] = _THEME_VERSION
