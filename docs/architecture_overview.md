# Architecture overview

## System purpose

Job Intelligence is a **human-in-the-loop** career workflow: parse a resume, rank job descriptions deterministically, approve roles, generate application packages, and view market/career snapshots. Matching logic lives in `career_intelligence_engine`; orchestration and persistence live in `career_agent_platform`.

**Release candidate scope:** Feature-complete for portfolio review. No new agents, integrations, or persistence layers in this phase — closure work focuses on metric rendering, narrative variation, regression verification, and demo documentation.

**Portfolio validation (2026-05-31):** 240+ automated tests passed; manual UI gate completed across all five pages. See [RELEASE_REPORT.md](RELEASE_REPORT.md) and [portfolio_summary.md](portfolio_summary.md).

## Layers

```
┌─────────────────────────────────────────────────────────┐
│  Streamlit multipage UI (Home.py, pages/*)              │
│  presentation/* — chips, theme, hero, market cards    │
├─────────────────────────────────────────────────────────┤
│  Platform services                                      │
│  • RecommendationEngine, ReviewQueueManager             │
│  • ApplicationPackageBuilder, MarketIntelligenceService │
│  • CanonicalResumeStore, DecisionMemory                 │
├─────────────────────────────────────────────────────────┤
│  career_intelligence_engine (deterministic)             │
│  • CareerIdentityEngine, JobMatchEngine                 │
│  • narrative_phrasing, match_explainability             │
│  • Ontology, eligibility matrix, career distance        │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   st.session_state              JSON files on disk
   (cache per browser tab)       (restart-safe source)
```

## Streamlit pages

| Page | Responsibility |
|------|----------------|
| **Overview (Home)** | Journey rail, version, entry to workflow |
| **Recommendations** | Resume ingest, JD ingest, generate ranked recs, review queue actions |
| **Market opportunities** | `build_market_snapshot(profile)` + curated feed cards with metric chips |
| **Application workspace** | Approved queue → tailored resume, cover letter, prep artifacts, export |
| **Career cockpit** | Strategic tiles, pipeline packages, skill-gap guidance |

## Presentation layer (metric rendering)

Fit and Confidence scores render via `presentation/chips.metric_chips_html`:

- Block-level label + value spans with **inline CSS fallback** (prevents `Fit66%Confidence90%` when theme CSS is late)
- Global theme in `presentation/theme.py` (`inject_global_styles` via sidebar nav)
- Career cockpit uses `render_cockpit_tile` with matching inline tile styles
- PDF/TXT export includes labeled `Match scores: Fit: X% · Confidence: Y%` from recommendation snapshot

## Narrative & explainability

- **Engine:** `narrative_phrasing.py` — strength/gap templates with deterministic rotation by role context
- **Platform:** `recommendation_engine._fit_lens_labels` — fit lens variants keyed by job title/company/family
- **UI dedup:** `presentation/explainability.py` — drops repeated bullets between summary, strengths, and signals

## Session vs disk

- **`st.session_state`**: In-memory cache for the active browser session (recommendations list, engines, profile).
- **Disk JSON**: Review queue, packages, canonical resumes, active resume marker — survives process restart.

On cold start, the platform **rehydrates** session caches from disk where possible (queue → recommendations, marker → profile). See [persistence_flow.md](persistence_flow.md).

## Market Opportunities dependency chain

1. User generates recommendations → `CandidateProfile` + canonical resume persisted.
2. `st.session_state.career_profile` set for the session.
3. Market page reads `career_profile`; if missing, falls back to `get_active_resume()` → `parsed_profile` on disk.
4. `build_market_snapshot(profile)` runs entirely in-process (no external APIs).

If step 1 persistence fails silently, Market and Career Cockpit can appear empty after restart even when queue entries exist.

## Observability

Structured ops logs (`career_agent.ops`) cover generation, persistence, restore, and package build timing. Configure via `CAREER_AGENT_LOG_LEVEL` (default `INFO`). App version: `career_agent_platform/version.py`.

## Demo & verification

- Walkthrough (expected outcomes): [demo_walkthrough.md](demo_walkthrough.md)
- Presenter script: [demo_script.md](demo_script.md)
- Portfolio brief: [portfolio_summary.md](portfolio_summary.md)
- Code quality audit: [code_quality_audit.md](code_quality_audit.md)
- Pre-release gate: [release_candidate_checklist.md](release_candidate_checklist.md)
- Release validation: [RELEASE_REPORT.md](RELEASE_REPORT.md)

## Diagrams

See [architecture_diagram.md](architecture_diagram.md) and [persistence_diagram.md](persistence_diagram.md) for Mermaid figures.

## Out of scope (by design)

- Auto-apply / browser automation (scaffold only)
- Database migrations
- External telemetry vendors
- Learned ranking weights
