# Demo script — Job Intelligence (release candidate)

**Duration:** 12–15 minutes  
**Audience:** Engineering reviewers, hiring managers evaluating portfolio architecture  
**Data:** Use `career_agent_platform/demo/public/sample_resume.txt` and **Load sample job feed** (fictional employers only).

**Step-by-step outcomes:** [demo_walkthrough.md](demo_walkthrough.md)
---

## 1. Overview (Home) — 2 min

1. From `career_agent_platform/`: `streamlit run Home.py`
2. Confirm sidebar navigation: Overview, Recommendations, Market opportunities, Application workspace, Career cockpit
3. Point out the reviewer journey rail and version badge
4. **Say:** "Human-in-the-loop career workflow — deterministic scoring, JSON persistence, no auto-apply."

**Screenshot:** `docs/screenshots/01-overview.png`

---

## 2. Recommendations — 4 min

1. Open **Recommendations**
2. Paste sample resume (or upload a sanitized PDF)
3. Enable **Load sample job feed** if no JDs on disk
4. Click **Generate recommendations**
5. Show ranked cards:
   - Fit and Confidence render as **separate metric chips** (not concatenated text)
   - Priority badge, brief, strengths/gaps, signals
6. Approve **two** strong-fit roles (not LOW_MATCH / gated roles)
7. Optionally expand **Details (explainability)** — note varied narrative phrasing per role

**Screenshot:** `docs/screenshots/02-recommendations.png`

---

## 3. Market opportunities — 2 min

1. Open **Market opportunities**
2. Confirm profile restored from session or canonical resume
3. Walk through: best-fit companies, role families, skill gaps
4. If using curated feed tab: open **Search on LinkedIn** for 2–3 listings — URLs must be real search links (no `example.com`, no synthetic job IDs)

**Screenshot:** `docs/screenshots/03-market.png`

---

## 4. Application workspace — 3 min

1. Open **Application workspace**
2. Select an approved role from the queue
3. Generate application package
4. Show hero: Fit/Confidence chips, positioning paragraph, strengths/gaps
5. Browse tabs: tailored resume, cover letter, recruiter messages, interview prep
6. Export PDF/TXT — confirm **Match scores: Fit: X% · Confidence: Y%** header in export

**Screenshot:** `docs/screenshots/04-workspace.png`

---

## 5. Career cockpit — 2 min

1. Open **Career cockpit**
2. Review intelligence tiles (role family, dimensions, market fit, readiness)
3. Confirm pipeline package count matches workspace
4. Expand a recent package — why matched / gaps

**Screenshot:** `docs/screenshots/05-dashboard.png`

---

## 6. Persistence check — 2 min

1. Stop Streamlit completely (Ctrl+C)
2. Restart `streamlit run Home.py`
3. Confirm: queue entries, approved roles, packages, and career profile still present
4. No demo/sample data resurrection if you were in normal (non-demo) mode

---

## Talking points

| Theme | Message |
|-------|---------|
| Determinism | Same resume + JD → same scores; golden snapshot tests lock behavior |
| Explainability | Strengths, gaps, fit lenses — recruiter-readable, not raw vectors |
| Persistence | Queue + canonical resume survive process restart |
| Scope boundary | No LLM required for core path; no automated job applications |

---

## Troubleshooting

- **Empty Market/Cockpit after restart or cross-page navigation:** Re-generate recommendations in the **same session** with **Load sample job feed** enabled so `parsed_profile` is written to the canonical resume. Queue restore alone does not hydrate `career_profile` on Market/Cockpit (see [RELEASE_REPORT.md](RELEASE_REPORT.md) DEF-001).
- **Metric chips look concatenated:** Hard-refresh browser; theme version `reviewer-ux-4` injects inline chip styles.
- **Demo mode:** Set `CAREER_AGENT_DEMO_MODE=1` — persistence disabled, banner visible.

## Validation evidence (2026-05-31)

Screenshots captured during portfolio-readiness gate:

| File | Scene |
|------|--------|
| `docs/screenshots/01-overview.png` | Overview — journey rail + version |
| `docs/screenshots/02-recommendations.png` | Recommendations — engine room + lifecycle pills |
| `docs/screenshots/03-market.png` | Market opportunities — empty state (visit after generate for populated view) |
| `docs/screenshots/04-workspace.png` | Application workspace — approved job + package switcher |
| `docs/screenshots/05-dashboard.png` | Career cockpit — pipeline + recent packages |

See [DEVELOPER.md](DEVELOPER.md), [release_candidate_checklist.md](release_candidate_checklist.md), and [RELEASE_REPORT.md](RELEASE_REPORT.md).
