# Portfolio summary — Job Intelligence

**Release:** `0.5.1`  
**Validated:** 2026-05-31  
**Audience:** Hiring managers, technical program leaders, engineering leadership

---

## Business problem

Job seekers and career operators typically juggle **disconnected tools**: resume parsers, spreadsheet trackers, ad-hoc job boards, and one-off cover letters. Decisions are hard to audit, rankings change unpredictably when LLMs are involved, and application state is lost when a browser tab closes.

Job Intelligence addresses this as a **single deterministic workflow**:

1. Parse a resume into an explainable career profile.
2. Rank job descriptions with transparent scores and recruiter-readable briefs.
3. Enforce **human approval** before any application artifact is generated.
4. Persist queue, profile, and packages across **process restarts** without a database.

Scope is intentionally bounded: **no auto-apply**, no external job APIs in the default path, no learned ranking weights.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Streamlit multipage UI (Overview → Recs → Market →        │
│  Workspace → Career cockpit)                                │
├─────────────────────────────────────────────────────────────┤
│  career_agent_platform — orchestration, persistence, UX     │
│  • RecommendationEngine, ReviewQueueManager                 │
│  • ApplicationPackageBuilder, MarketIntelligenceService     │
│  • CanonicalResumeStore, ops logging                        │
├─────────────────────────────────────────────────────────────┤
│  career_intelligence_engine — deterministic matching        │
│  • Ontology, eligibility, career distance, explainability │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   st.session_state              JSON files on disk
```

**Runtime note:** The platform embeds a copy of the engine under `career_agent_platform/career_intelligence_engine/` (109 mirrored modules). `PYTHONPATH=career_agent_platform` selects the embedded tree at runtime.

Deep dive: [architecture_overview.md](architecture_overview.md) · [architecture_diagram.md](architecture_diagram.md)

---

## Technical decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Matching | Deterministic ontology + gates | Reproducible rankings; auditable for recruiters |
| UI | Streamlit multipage | Fast human-in-the-loop iteration; low ops overhead |
| Persistence | JSON files | Restart recovery without DB migrations |
| Scoring changes | Golden snapshot regression | Lock behavior across releases |
| LLM | Optional scaffold only | Core path does not depend on model variance |
| CI | Platform tests required; benchmark drift informational | Separate product truth from fixture staleness |

---

## Why deterministic ranking was chosen

1. **Trust** — Same resume + same job postings → same Fit/Confidence and sort order every time.
2. **Governance** — Recommendation hash, ontology version, and benchmark signature logged after each generation run.
3. **Explainability** — Strengths, gaps, and fit lenses are template-driven and reviewable, not opaque embeddings.
4. **Regression control** — Golden fixtures under `evaluation/golden/` catch unintended orchestration drift without retuning weights in CI failures.
5. **Portfolio narrative** — Demonstrates systems thinking (evaluation layer, ops logs, persistence) rather than prompt engineering alone.

See [evaluation_strategy.md](evaluation_strategy.md) and `career_agent_platform/version.py` (`DETERMINISM_NOTE`).

---

## Governance approach

| Layer | Mechanism |
|-------|-----------|
| Human gate | Approve / reject / archive in review queue before packages |
| Diagnostics | Governance panel: hash, ontology version, deterministic mode flag |
| Demo safety | `CAREER_AGENT_DEMO_MODE=1` blocks persistence writes |
| Data hygiene | Listing URL scrubber removes `example.com`, preview IDs, synthetic job links |
| Risk register | [operational_risks.md](operational_risks.md) — silent persist failures, queue races |
| Release evidence | [RELEASE_REPORT.md](RELEASE_REPORT.md) — defects with workarounds |

---

## Challenges solved

| Challenge | Solution |
|-----------|----------|
| Streamlit restart drops session | Rehydrate queue + canonical resume from disk on cold start |
| Metric chips rendering as concatenated text | Inline CSS fallback in `presentation/chips.py` |
| Cross-page profile gaps | Documented DEF-001; demo requires generate before Market/Cockpit |
| Stale demo data resurrection | Demo purge guards + separate `demo/public/` artifacts |
| Engine/platform drift | Golden snapshots + dual-tree awareness in docs |
| Recruiter-unreadable scores | Briefs, strengths/gaps, export headers with labeled match scores |

---

## Testing strategy

| Layer | Command / artifact | Gate |
|-------|-------------------|------|
| Platform unit/integration | `pytest career_agent_platform/tests` | CI required |
| Golden recommendations | `tests/test_golden_recommendations.py` | CI required |
| Demo mode | `tests/test_demo_mode.py` | CI required |
| Engine regression | `pytest career_intelligence_engine/tests` (benchmark file excluded) | CI required |
| Benchmark adjacency | `test_benchmark_rankings.py` | Informational (4 known failures) |
| Public demo artifacts | `demo/generate_public_snapshots.py` | CI validation |
| Manual UI | [demo_walkthrough.md](demo_walkthrough.md) | Portfolio demo |

**240+ automated tests** passed at release validation (see RELEASE_REPORT).

---

## TPM leadership examples

Use these talking points when presenting to program or delivery leadership:

1. **Release gating with explicit non-blockers** — Separated CI-blocking tests from informational benchmark drift; documented in `benchmark_drift_notes.md` instead of silent score tuning.
2. **Operational readiness without SaaS scope** — Structured ops logging (`career_agent.ops`), version metadata, and defect register (DEF-001–005) with demo workarounds.
3. **Human-in-the-loop by design** — Approval queue as workflow state machine; no automated applications; aligns with compliance-minded hiring workflows.
4. **Evaluation layer as product discipline** — Golden snapshots, diff utilities, and governance hashes mirror how TPM orgs run regression programs on fixed requirements.
5. **Cross-functional UX contract** — Fit/Confidence presentation spec shared across Recommendations, Workspace export, and Career cockpit tiles.
6. **Risk transparency** — `operational_risks.md` catalogs silent failure zones and concurrent-tab races without hiding behind "works on my machine."

---

## Five-minute demo path

| # | Page | Proof |
|---|------|-------|
| 1 | Overview | Navigation + version |
| 2 | Recommendations | Resume → ranked cards → approve 2+ |
| 3 | Market opportunities | Fit snapshot (same session) |
| 4 | Application workspace | Package + export |
| 5 | Career cockpit | Counts reconcile |

Walkthrough: [demo_walkthrough.md](demo_walkthrough.md) · Screenshots: [screenshots/README.md](screenshots/README.md)

---

## Repository map

| Path | Role |
|------|------|
| `career_agent_platform/` | Streamlit app, persistence, evaluation |
| `career_intelligence_engine/` | Canonical deterministic engine |
| `docs/` | Architecture, demo, release, audit |
| `.github/workflows/ci.yml` | Automated regression |

---

## Verdict

**Production-demo ready** for portfolio and recruiter sessions when the presenter follows the demo walkthrough (generate before Market/Cockpit). **GitHub publication** requires LICENSE + committed screenshots (see [code_quality_audit.md](code_quality_audit.md)).
