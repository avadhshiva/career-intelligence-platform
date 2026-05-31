# Interview talking points — Job Intelligence

**Release:** `0.5.1`  
**Audience:** Hiring managers, technical program leaders, engineering leadership, architecture reviewers

Use this document to prepare for portfolio reviews, system design interviews, and TPM/PM leadership conversations.

---

## Why this project was built

### The problem I wanted to solve

Job seekers and career operators typically stitch together disconnected tools — resume parsers, spreadsheets, job boards, and one-off LLM prompts. The result is a workflow that is:

- **Hard to audit** — rankings change unpredictably when models are involved.
- **Hard to trust** — no reproducible evidence for why one role ranked above another.
- **Hard to recover** — closing a tab or restarting the app loses approvals and packages.
- **Hard to defend** — auto-apply tools bypass human judgment on role fit.

### What I set out to demonstrate

Job Intelligence is a **portfolio artifact** that shows systems thinking beyond prompt engineering:

1. **Deterministic matching** — same inputs produce the same scores every time.
2. **Human-in-the-loop governance** — explicit approval gates before any application artifact.
3. **Restart-safe persistence** — JSON files recover queue, profile, and packages without a database.
4. **Evaluation discipline** — golden snapshot regression, CI gates, and a documented defect register.
5. **Recruiter-readable UX** — Fit/Confidence chips, explainability expanders, labeled export scores.

### Scope boundary (intentional)

This is **not** auto-apply SaaS. I deliberately excluded external job APIs, LLM-dependent ranking, authentication, cloud deployment, and agent orchestration from the frozen release. The focus is workflow engineering, explainability, and program discipline.

---

## System architecture decisions

### Three-layer separation

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **UI** | `Home.py`, `pages/*`, `presentation/*` | Navigation, metric chips, journey rail, governance expander |
| **Platform** | `career_agent_platform/` | Orchestration, persistence, review queue, package builder, market service |
| **Engine** | `career_intelligence_engine/` | Ontology, eligibility, matching, explainability — deterministic, no LLM |

**Why separate engine from platform?**

- The engine is a **pure scoring and identity module** — testable in isolation with 123+ unit tests.
- The platform handles **Streamlit session state, disk I/O, and workflow state machines** — concerns the engine should not know about.
- This mirrors how real organizations split "scoring service" from "workflow orchestration."

### Streamlit as the UI framework

**Chosen because:**

- Fast iteration for human-in-the-loop workflows (approve/reject buttons, expanders, tabs).
- Low operational overhead — no frontend build pipeline for a portfolio demo.
- Multage routing maps cleanly to the five-step career journey.

**Tradeoff accepted:**

- Session state is per-browser-tab; disk is the restart source of truth.
- Concurrent tabs can race on `review_queue.json` (DEF-005) — documented, not hidden.

### JSON file persistence (no database)

**Chosen because:**

- Restart recovery without migrations or infra setup.
- Artifacts are inspectable — reviewers can open `review_queue.json` and see workflow state.
- Demo-safe mode can block writes with a single env flag.

**Tradeoff accepted:**

- Last-write-wins under concurrent tabs.
- No transactional guarantees — acceptable for single-user portfolio demo.

### Dual engine tree (embedded copy)

The platform embeds a runtime copy of the engine under `career_agent_platform/career_intelligence_engine/` (109 mirrored modules). `PYTHONPATH=career_agent_platform` selects the embedded tree.

**Why:**

- Streamlit runs from the platform directory; embedding avoids import path gymnastics.
- Golden snapshots test the **runtime path**, not just the canonical tree.

**Risk:**

- Drift between root and embedded copies. Mitigation: documented in roadmap; spot-check hashes match at release.

---

## Deterministic ranking rationale

### Why not LLM-based matching?

| Concern | LLM approach | Deterministic approach |
|---------|------------|------------------------|
| Reproducibility | Scores vary run-to-run | Same resume + JDs → same scores |
| Auditability | Opaque embeddings | Weighted dimensions with named gates |
| Regression control | Prompt drift breaks tests | Golden hash snapshots lock behavior |
| Recruiter trust | "The AI said so" | "Capability similarity 45%, eligibility 20%…" |
| Portfolio narrative | Prompt engineering | Systems engineering + evaluation layer |

### Scoring model (JobMatchEngine)

Fixed weights — no randomness, no learned parameters:

| Dimension | Weight |
|-----------|--------|
| Capability similarity | 0.45 |
| Eligibility fit | 0.20 |
| Seniority fit | 0.10 |
| Transformation fit | 0.10 |
| Architecture fit | 0.08 |
| Governance fit | 0.07 |

Gates, cosine similarity on capability vectors, seniority distance, and ontology lookups produce `overall_match_score`. Results are **stable-sorted** in `RecommendationEngine._stable_rank`.

### What "deterministic" means in practice

- Regenerating recommendations with the same resume and job feed produces identical Fit/Confidence values and sort order.
- Golden snapshot tests hash the full recommendation output — CI fails on any drift.
- `version.py` documents `DETERMINISM_NOTE` explicitly.

### When I would add LLMs (future, out of scope)

- Optional narrative polish on approved packages — **after** human gate, not before ranking.
- Never as the primary scoring mechanism without a parallel deterministic baseline.

---

## Explainability strategy

### Three layers of explanation

| Layer | Mechanism | Audience |
|-------|-----------|----------|
| **Card summary** | Fit/Confidence chips, priority badge, one-line brief | Recruiter scanning |
| **Details expander** | Strengths, gaps, fit lenses (governance/architecture/execution) | Hiring manager review |
| **Governance panel** | Recommendation hash, ontology version, benchmark signature, snapshot ID | Engineering/audit |

### Template-driven narratives (not model output)

- `narrative_phrasing.py` — strength/gap templates with deterministic rotation by role context.
- `_fit_lens_labels` — fit lens variants keyed by job title, company, and role family.
- `presentation/explainability.py` — deduplicates repeated bullets between summary, strengths, and signals.

**Why templates over LLM explanations?**

- Explanations are **reviewable in code** — no hallucinated strengths.
- Same inputs → same explanation text → regression-testable.
- Recruiters see consistent, professional language across all cards.

### Export explainability

PDF and TXT exports include labeled match scores: `Match scores: Fit: X% · Confidence: Y%` plus strengths/gaps from the recommendation snapshot.

---

## Governance model

### Human gate (primary control)

```
Generate recommendations → Pending review → [Approve | Reject | Archive]
                                              ↓ (approve only)
                                    Application package generation
```

No package is created without explicit human approval. This aligns with compliance-minded hiring workflows and demonstrates intentional scope control.

### Technical governance (secondary control)

| Mechanism | Purpose |
|-----------|---------|
| Recommendation hash | Detect if scoring inputs/outputs changed between runs |
| Ontology version | Track which skill/eligibility matrix was active |
| Benchmark signature | Link generation to known fixture baseline |
| Demo mode flag | Block persistence writes during public demos |
| URL hygiene | Strip `example.com`, preview job IDs, synthetic listing links |

### Risk register (transparency)

`operational_risks.md` catalogs silent persist failures, queue row parse skips, concurrent-tab races, and dual-engine drift — without hiding behind "works on my machine."

### Release gating discipline

- **CI-blocking:** Platform tests, golden snapshots, demo mode, engine regression.
- **Informational:** Benchmark adjacency drift (4 known failures) — documented in `benchmark_drift_notes.md`, not silently retuned.

---

## Human-in-the-loop workflow

### State machine

```
PendingReview → Approved → PackageGenerated → Applied → Archived
             → Rejected  → Archived
```

### Why human-in-the-loop is a feature, not a limitation

1. **Compliance** — hiring workflows require human judgment on role fit.
2. **Quality** — weak matches are rejected before wasting tailoring effort.
3. **Audit trail** — decision memory tab records approve/reject history.
4. **Portfolio signal** — shows I understand when automation should stop.

### Demo-safe mode

`CAREER_AGENT_DEMO_MODE=1` blocks all persistence writes. Presenters can generate and approve in-session without leaving artifacts on disk. Tested in CI (4 tests).

---

## TPM leadership examples

Use these when interviewers ask "how would you run this as a program?"

### 1. Release gating with explicit non-blockers

I separated CI-blocking tests (platform, golden, engine) from informational benchmark drift (4 adjacency failures). Instead of silently retuning weights to make benchmarks pass, I documented the drift, excluded it from the release gate, and tracked it in `benchmark_drift_notes.md`. This mirrors how TPM orgs handle "known issues" vs "ship blockers."

### 2. Defect register with demo workarounds (DEF-001 through DEF-005)

Every known issue has an ID, severity, workaround, and release-blocker flag. DEF-001 (cross-page profile hydration) has a documented demo script workaround — generate before visiting Market/Cockpit. No hidden failures.

### 3. Evaluation layer as product discipline

Golden snapshots under `evaluation/golden/` with manifest hashes. CI regenerates and diffs — any drift fails the build. This is the same regression philosophy TPM teams use for fixed requirements baselines.

### 4. Cross-functional UX contract

Fit/Confidence presentation is shared across Recommendations cards, Application workspace hero, Career cockpit tiles, and PDF/TXT export headers. One metric spec, four surfaces — reduces reviewer confusion.

### 5. Operational readiness without SaaS scope

Structured ops logging (`career_agent.ops`), version metadata in `version.py`, startup smoke tests, and public demo artifact generation in CI. Production-minded observability on a portfolio app.

### 6. Scope freeze as program decision

At `0.5.1`, I declared feature-complete and stopped adding agents, APIs, RAG, vector DBs, and new pages. The roadmap is evaluation tooling and hygiene — not feature creep. This demonstrates prioritization under constraint.

### 7. Documentation as deliverable

Architecture overview, persistence flow, demo walkthrough, release report, code quality audit, screenshot index, and this interview guide — all shipped as part of the release, not as afterthought.

---

## Tradeoffs made

| Tradeoff | Chosen | Alternative rejected | Why |
|----------|--------|---------------------|-----|
| Matching engine | Deterministic ontology | LLM embeddings | Reproducibility, auditability, regression control |
| Persistence | JSON files | PostgreSQL/SQLite | Zero infra for portfolio demo; inspectable artifacts |
| UI framework | Streamlit | React + FastAPI | Speed to demo; human-in-the-loop buttons/expander UX |
| Engine packaging | Embedded copy in platform | pip-installable package | Simpler PYTHONPATH for Streamlit entry; golden tests runtime path |
| Benchmark failures | Document + exclude from gate | Retune weights to pass | Avoids silent scoring changes; preserves determinism proof |
| Auto-apply | Scaffold only | Playwright automation | Compliance risk; out of portfolio scope |
| Authentication | None | OAuth/login | Single-user demo; adds infra without portfolio signal |
| External job APIs | None in default path | LinkedIn/Indeed APIs | Rate limits, ToS, demo fragility |
| Concurrent tabs | Last-write-wins | File locking | Complexity vs single-tab demo reality |
| Cross-page profile | Session + disk fallback | Always re-parse on navigation | Performance; documented DEF-001 workaround |

---

## Quick reference for common interview questions

| Question | Answer in one sentence |
|----------|-------------------------|
| Why deterministic? | Same inputs → same scores; auditable, regression-testable, recruiter-trustworthy. |
| Why no LLM? | Portfolio demonstrates systems engineering, not prompt engineering; LLM variance breaks golden tests. |
| Why Streamlit? | Fast human-in-the-loop UX for portfolio demo; low ops overhead. |
| Why JSON not DB? | Restart recovery without migrations; inspectable artifacts for reviewers. |
| Biggest known issue? | DEF-001 — Market/Cockpit empty without `parsed_profile` on disk; workaround in demo script. |
| How do you prevent regression? | Golden snapshot hashes in CI; 240+ automated tests; informational benchmark drift excluded from gate. |
| What would you add next? | Evaluation layer (0.6.0), file locking, cross-page profile hydration — not new features. |
| How is this different from ChatGPT job matching? | Explicit weights, human approval gate, persistence, governance hash, no model variance. |

---

## Related documents

| Document | Purpose |
|----------|---------|
| [recruiter_demo_script.md](recruiter_demo_script.md) | 5-minute live demo |
| [portfolio_summary.md](portfolio_summary.md) | Executive brief |
| [architecture_overview.md](architecture_overview.md) | Layer responsibilities |
| [evaluation_strategy.md](evaluation_strategy.md) | Regression philosophy |
| [RELEASE_REPORT.md](RELEASE_REPORT.md) | Validation evidence and defects |
| [operational_risks.md](operational_risks.md) | Silent failure catalog |
