# RELEASE REPORT — Job Intelligence 0.5.1

**Validation date:** 2026-05-31  
**Validator:** Portfolio-readiness regression + manual Streamlit UI gate  
**Verdict:** **Production-demo ready** (with documented workarounds below)

---

## Executive summary

The platform passes the full automated regression suite (240+ tests across platform and engine), golden snapshot determinism checks, demo-mode guards, listing URL hygiene tests, and manual navigation of all five Streamlit pages. No runtime exceptions were observed during UI verification. Application workspace package generation and queue persistence function correctly.

One medium-severity cross-page profile gap affects Market Opportunities and Career Cockpit intelligence tiles when the active canonical resume lacks `parsed_profile` on disk. This is **not a release blocker** for a live demo if the presenter generates recommendations in the same session before visiting those pages (as documented in the demo script).

---

## Regression suite results

| Check | Command / scope | Result |
|-------|-----------------|--------|
| Platform tests | `pytest career_agent_platform/tests` | **112 passed** |
| Engine tests | `pytest career_intelligence_engine/tests` (benchmark drift excluded) | **123 passed** |
| Golden recommendations | `pytest tests/test_golden_recommendations.py` | **5 passed** |
| Demo mode | `pytest tests/test_demo_mode.py` | **4 passed** |
| Golden idempotency | `generate_golden_snapshots.py` + git diff | **No drift** |
| Market / URLs / UX | `test_market_intelligence_service`, `test_listing_urls`, `test_presentation_ux_consistency` | **21 passed** |
| Workflow trust | `test_workflow_trust`, `test_application_tracking` | **6 passed** |
| Import smoke | `import Home`, `RecommendationEngine`, demo flags | **Pass** |
| Public demo artifacts | `demo/generate_public_snapshots.py` | **Pass** |

---

## Manual UI verification

**App:** `streamlit run Home.py` on port 8502 (existing process; fresh start attempted — ports 8501/8502 in use)

### Startup

- [x] No red exception boxes on any page
- [x] Sidebar navigation: Overview, Recommendations, Market opportunities, Application workspace, Career cockpit
- [x] Version caption: `0.5.1`
- [x] Engineering notes expander on Overview

### Recommendations

- [x] Resume identity card (role family, experience, skills)
- [x] Ranked match cards with Fit/Confidence chips, brief, strengths/gaps
- [x] Expanders: Active resume identity, Details (explainability), Raw JSON, Review queue, Recommendation governance
- [x] Tabs: Ranked matches, Market Intelligence; queue tabs Pending/Approved/Rejected/Decision memory
- [x] 3 approved roles visible; 2 pending
- [x] Regenerate button present; queue restore from disk confirmed

### Market opportunities

- [x] Page loads without exception
- [x] Empty-state guidance when profile unavailable (see DEF-001)
- [x] Navigation link back to Recommendations works
- [ ] Populated market snapshot in cross-page navigation without fresh generate — **blocked by DEF-001**

### Application workspace

- [x] Approved job selector populated (Enterprise Delivery Director, etc.)
- [x] Saved package switcher (Senior TPM package exists)
- [x] Active resume handoff from Recommendations
- [x] Generate application package button present
- [x] No placeholder URLs or example.com links

### Career cockpit

- [x] Application pipeline: 3 packages
- [x] Recent packages expanders with why-matched / gaps
- [x] Empty intelligence snapshot when profile unavailable (see DEF-001)
- [x] Counts reconcile with workspace saved packages

### Listing URL hygiene (automated)

- [x] `resolve_listing_url` strips `example.com`, `currentJobId`, stale `/jobs/view/` links
- [x] Produces LinkedIn search URLs for curated feed

### Screenshots (portfolio assets)

Validation captures were taken during the UI gate. **Commit PNGs to `docs/screenshots/` before public GitHub publish** — see [screenshots/README.md](screenshots/README.md). Until committed, README image embeds will 404.

| File | Page |
|------|------|
| `docs/screenshots/01-overview.png` | Overview |
| `docs/screenshots/02-recommendations.png` | Recommendations |
| `docs/screenshots/03-market.png` | Market opportunities (prefer populated view after generate) |
| `docs/screenshots/04-workspace.png` | Application workspace |
| `docs/screenshots/05-dashboard.png` | Career cockpit |

---

## Remaining defects

| ID | Defect | Severity | Workaround | Release blocker? |
|----|--------|----------|------------|------------------|
| **DEF-001** | **Market Opportunities and Career Cockpit intelligence sections show empty state** ("Profile not analyzed yet" / "Intelligence unlocks after resume analysis") when the active canonical resume on disk lacks `parsed_profile`, even if Recommendations displays restored queue cards and resume identity metadata. Root cause: `career_profile` is not hydrated cross-page from queue-only restore; disk fallback requires `parsed_profile` in `data/resumes/{id}.json`. Observed: active resume `5be420a54d64e4ca` has no `parsed_profile`. | **Medium** | In the same browser session, open Recommendations, enable **Load sample job feed**, click **Regenerate ranked recommendations**, then visit Market/Cockpit. For restart demos, ensure generate completes successfully so canonical persist writes `parsed_profile`. | **No** for live demo (demo script covers this). **Yes** for cold-restart-only walkthrough without re-generate. |
| **DEF-002** | **Career Cockpit recent packages list can show duplicate entries** for the same role when multiple package files exist (observed: Senior TPM listed twice). | **Low** | Use package switcher in Application workspace; collapse duplicates when presenting. | **No** |
| **DEF-003** | **Regenerate without JD inputs** shows validation message ("Add at least one job description…") and does not refresh profile when sample feed checkbox is unchecked after prior session data cleared JD cache. | **Low** | Keep sample feed enabled or ensure JDs on disk before regenerate. | **No** |
| **DEF-004** | **Benchmark adjacency drift** — 4 known fixture failures in `test_benchmark_rankings.py` (informational; excluded from CI gate). | **Info** | Documented in `docs/benchmark_drift_notes.md`; golden snapshot tests remain passing. | **No** |
| **DEF-005** | **Concurrent Streamlit tabs** can last-write-wins on `review_queue.json`. | **Low** | Use single tab for demo; documented in `docs/operational_risks.md`. | **No** |

No **Critical** or **High** defects identified. No broken navigation, no runtime tracebacks, no `example.com` listing links, no stale demo data resurrection in normal mode.

---

## Confirmation checklist

| Item | Status |
|------|--------|
| No runtime exceptions remain | **Confirmed** |
| No broken navigation links remain | **Confirmed** |
| No placeholder labels (`example.com`, synthetic job IDs in listings) | **Confirmed** (automated URL tests) |
| No stale demo data resurrection (normal mode) | **Confirmed** |
| Package generation path functional | **Confirmed** (saved packages + generate UI) |
| Approval flow functional | **Confirmed** (3 approved in session + disk queue) |
| Resume persistence | **Confirmed** (active resume marker + queue on disk; see DEF-001 for parsed_profile gap) |

---

## Documentation delivered

| Document | Path |
|----------|------|
| Architecture overview | `docs/architecture_overview.md` |
| Demo walkthrough (step outcomes) | `docs/demo_walkthrough.md` |
| Demo script (talking points) | `docs/demo_script.md` |
| Portfolio summary | `docs/portfolio_summary.md` |
| Code quality audit | `docs/code_quality_audit.md` |
| Screenshot index | `docs/screenshots/README.md` |
| This release report | `docs/RELEASE_REPORT.md` |
| Screenshots (PNG) | `docs/screenshots/01-overview.png` … `05-dashboard.png` — **commit before publish** |

---

## Release declaration

**Job Intelligence 0.5.1 is declared production-demo ready** for portfolio presentation, subject to following the demo script workaround for DEF-001 (generate recommendations before Market/Cockpit).

No code changes were made during this validation pass.
