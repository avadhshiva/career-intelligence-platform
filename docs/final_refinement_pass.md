# Final refinement pass — recruiter perception

**Phase:** Executive polish only (no scoring, ontology, agents, or new dashboards).

## Issue list (prioritized)

| ID | Area | Issue | Severity |
|----|------|-------|----------|
| R1 | Recommendation cards | Strengths, gaps, and key drivers repeat the same lens phrases | High |
| R2 | Recommendation cards | Cards feel verbose; weak scan hierarchy (equal-weight bullets) | High |
| R3 | Metrics | Fit/Confidence can visually collapse to `Fit73%Confidence95%` without block CSS / narrow widths | High |
| R4 | Explainability | Deterministic templates read repetitive (“documented strength”, “aligns”, “below role bar”) | High |
| R5 | Information density | Page purpose blocks and section gaps leave excess vertical whitespace | Medium |
| R6 | Executive polish | Copy references “Positioning” on Recommendations but card had no brief line | Medium |
| R7 | Dark / export | Metric chips and cards lack dark-theme contrast rules | Medium |
| R8 | Market / cockpit | Mixed metric patterns (`st.metric` vs chips vs inline `%.0f`) | Low (defer) |
| R9 | PDF export | No dedicated PDF pipeline; rely on print CSS + chip structure | Low (monitor) |

## Implementation order

1. **R3 + R7** — Harden metric chip HTML/CSS (block layout, nowrap, dark theme, theme version bump).
2. **R4** — Refresh narrative phrasing and fit-lens copy; dedupe explainability assembly.
3. **R1 + R2 + R6** — Compact recommendation card layout + brief line + deduped drivers.
4. **R5** — Tighter global spacing rhythm (`theme.py`).
5. **Verification** — `pytest` presentation tests + fresh `streamlit run Home.py` + checklist screenshots.

## Before / after screenshots

Captured 2026-05-28 after `reviewer-ux-3` theme (fresh `streamlit run Home.py` on port 8501).

| File | Scene | Notes |
|------|--------|--------|
| `docs/screenshots/refine-01-recommendations-card.png` | Recommendations — ranked list + engine room | Full-page; expand a Good/Strong match to see Brief / Strengths / Gaps / Signals |
| `docs/screenshots/refine-02-recommendations-narrow.png` | Recommendations at 900px width | Metric chip layout regression check |
| `docs/screenshots/refine-03-workspace-hero.png` | Application workspace (pre-package) | Hero metrics appear after **Generate application package** |
| `docs/screenshots/refine-04-cockpit.png` | Career cockpit snapshot tiles | |
| `docs/screenshots/refine-05-overview.png` | Overview — updated enterprise purpose copy | |

`?preview=hero` loads frozen sample JSON; regenerated runs pick up new lens phrasing and brief tiers.

## Executed in this pass

- R3, R7, R4, R1, R2, R6, R5 (partial — theme + card only; cockpit metric unification deferred per constraints).

## Deferred (explicit)

- R8 unified metric component across all pages
- R9 PDF-specific renderer
- Demo JSON string refresh (regenerated on next recommendation run)
