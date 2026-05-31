# Code quality audit — Job Intelligence (release lockdown)

**Audit date:** 2026-05-31  
**Scope:** Documentation-only pass; **no functional code modified**  
**Tooling:** `ruff check --select F401` (platform tree), manual structure review, file-hash spot checks

---

## Executive summary

The codebase is **release-frozen** and suitable for portfolio review. Primary cleanup opportunities are **non-blocking**: unused imports, orphan scaffolds, committed artifacts, missing screenshots, and dual engine copies (documented architectural choice). None of these block a live demo when following [demo_walkthrough.md](demo_walkthrough.md).

---

## Dead code candidates

| Category | Path(s) | Rationale | Risk if removed |
|----------|---------|-----------|-----------------|
| Legacy FastAPI UI | `career_intelligence_engine/app/main.py`, `ui.py`, `visualizations.py` (+ embedded copy) | Streamlit (`Home.py`) is production entry | Low — verify no external consumers |
| Personal validation script | `scripts/validate_sivakumar_ranking.py` (×2) | Ad-hoc ranking check | None for product |
| Phase 5 browser stub | `career_agent_platform/browser/` | Documented "not implemented" | None |
| Empty package stubs | `orchestration/`, `configs/` `__init__.py` only | Placeholder packages | Low — may be future hooks |
| Agent scaffolds | `agents/human_review_agent.py`, `job_discovery_agent.py`, `resume_tailoring_agent.py` | Not imported by Streamlit pages | Low — covered by `test_phase5a_*` |
| Workflow pipeline | `workflows/recommendation_pipeline.py` | Only referenced by phase-5 tests | Low |

**Not classified as dead:** `hiring_intelligence/`, `job_sources/`, `memory/`, `evaluation/`, benchmark CLIs — used by pages or CI.

---

## Duplicate logic & files

### Dual `career_intelligence_engine` trees

| Location | Modules mirrored |
|----------|------------------|
| `career_intelligence_engine/` (canonical) | 109 Python modules |
| `career_agent_platform/career_intelligence_engine/` (runtime) | Same 109 paths + 2 embedded-only (`narrative_phrasing.py`, `tests/test_narrative_phrasing.py`) |

**Spot check:** `matching/job_match_engine.py` — identical MD5 hash in both trees.

**Recommendation (post-release):** Single-source packaging or sync script in CI; **do not dedupe during lockdown** without explicit scoring release.

### Duplicate documentation

| Files | Notes |
|-------|-------|
| `docs/demo_script.md` vs `docs/demo_walkthrough.md` | Complementary — script = talking points; walkthrough = step outcomes |
| Overlapping architecture in README, `architecture_overview.md`, `portfolio_summary.md` | Intentional layering for recruiters vs engineers |

---

## Unused imports (F401)

**Scan:** `ruff check career_agent_platform --select F401`  
**Result:** **48 findings** (auto-fixable; not applied in lockdown)

**Representative locations:**

| Module | Unused symbol |
|--------|----------------|
| `application_tracking/analytics.py` | `pathlib.Path`, `ApplicationRecord` |
| `application_tracking/followup_engine.py` | `ApplicationRecord` |
| `career_intelligence_engine/app/main.py` | `RoleFamilyId` |
| `tests/test_phase5a_recommendation_pipeline.py` | `pytest` (and similar test-only imports) |
| Various platform services | Occasional type-only or legacy imports |

**Recommendation:** Run `ruff check career_agent_platform --select F401 --fix` in a **post-portfolio hygiene PR** only.

---

## Unused / stray files (non-Python)

| Path | Recommendation |
|------|----------------|
| `career_agent_platform/test_out.txt` | Delete or gitignore — test artifact |
| `career_agent_platform/.tmp_qa/qa_resume.txt` | Delete or gitignore — local QA |
| `.pytest_cache/` | Already gitignored; do not commit |

---

## Broken references (documentation)

| Reference | Status |
|-----------|--------|
| `README.md` → `docs/screenshots/0*.png` | **Broken** — PNGs not committed (folder has README only) |
| `docs/RELEASE_REPORT.md` claims screenshots captured | **Stale claim** until PNGs added |
| All other `docs/*.md` cross-links | **Valid** (verified 2026-05-31) |
| CI badge `../../actions/workflows/ci.yml` | Valid GitHub Actions pattern |

---

## Broken navigation paths (application)

Streamlit `st.page_link` targets in `presentation/nav.py`:

| Label | Target | Status |
|-------|--------|--------|
| Overview | `Home.py` | OK |
| Recommendations | `pages/Job_Recommendations.py` | OK |
| Market opportunities | `pages/Market_Opportunities.py` | OK |
| Application workspace | `pages/Application_Workspace.py` | OK |
| Career cockpit | `pages/Application_Dashboard.py` | OK |

No broken in-app navigation paths identified.

---

## Cleanup opportunities (documentation & repo hygiene only)

| Priority | Action | Effort |
|----------|--------|--------|
| P0 | Commit five PNG screenshots to `docs/screenshots/` | 15 min |
| P0 | Add `LICENSE` (e.g. MIT) before public GitHub | 5 min |
| P1 | Align README version string with `0.5.1` | 5 min |
| P1 | Reconcile RELEASE_REPORT screenshot claim with repo state | 5 min |
| P2 | `ruff --select F401 --fix` on platform (48 imports) | 15 min |
| P2 | Remove `test_out.txt`, `.tmp_qa/` | 5 min |
| P3 | Archive or document FastAPI `app/` entry as legacy | 30 min |
| P3 | Engine deduplication strategy (CI sync check) | Multi-day (out of lockdown scope) |

---

## Test & quality signals (unchanged in lockdown)

| Signal | Status |
|--------|--------|
| Platform pytest | 112 passed (per RELEASE_REPORT) |
| Engine pytest (benchmark excluded) | 123 passed |
| Golden snapshots | 5 passed + idempotent regenerate |
| Demo mode guards | 4 passed |

---

## Lockdown compliance

This audit **did not** modify scoring, persistence, orchestration, ontology, or UI logic. Findings are recorded for **post-portfolio** hygiene only.
