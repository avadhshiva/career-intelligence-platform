# Evaluation strategy

Engineering evaluation layer for the deterministic recommendation platform. This document governs **comparison and regression awareness** without changing scoring, ranking, or ontology weights.

## Deterministic recommendation philosophy

- Same resume text + same job postings → same scores, priorities, and stable sort order.
- No LLM in the default recommendation path (`career_agent_platform/version.py` `DETERMINISM_NOTE`).
- Human-in-the-loop gates (approve / reject / archive) are **workflow state**, not model variance.
- Platform orchestration may enrich display metadata (normalization, routing labels) but must not alter `overall_match` or priority buckets.

## Benchmark drift handling

Four benchmark guardrail tests currently fail (adjacency and program-cluster expectations). These are **documented, non-blocking** for CI:

| Category | CI treatment | Production meaning |
|----------|--------------|-------------------|
| Adjacency expectation miss | Informational | Engine may be correct; fixture `expected_adjacent` may be stale |
| Program cluster top-4 slot | Informational | New families (e.g. `ai_program_management`) in ranking pool |
| Aggregate `23/25` adjacency | Informational | Tracked via `benchmark_signature` in ops logs |
| Score drift vs baseline | Optional local check | Requires intentional baseline regeneration |

CI runs `career_agent_platform/tests` and engine tests **excluding** `test_benchmark_rankings.py`. The separate `benchmark.yml` workflow remains for ontology calibration review.

## Adjacency expectations

Adjacency is evaluated at two layers:

1. **Candidate profile** — `primary_career_track` and `adjacent_role_families` from identity analysis.
2. **Job role family** — `JobProfile.primary_role_family` per posting.

Recommendation diagnostics expose adjacency reasoning in `match_detail.diagnostics` (primary match, adjacent match, or outside set). This supports governance review without changing rank order.

## Ranking validation strategy

| Layer | Method | Blocks release? |
|-------|--------|-----------------|
| Unit / integration | `pytest career_agent_platform/tests` | Yes (CI) |
| Engine regression snapshots | `test_regression.py` | Yes (CI) |
| Benchmark adjacency contract | `test_benchmark_rankings.py` | No (informational) |
| Recommendation snapshots | `evaluation/recommendation_snapshot.py` | On intentional diff review |
| Public demo artifacts | `demo/generate_public_snapshots.py` in CI | Yes (CI) |

Snapshot comparison fields: `job_id`, `overall_match`, `recommendation_priority`, `primary_role_family`, ordering.

## Regression philosophy

1. **Do not** “fix” benchmark failures by tuning scores unless product intent changes.
2. **Do** capture recommendation snapshots before/after ontology or orchestration changes.
3. **Treat** snapshot diffs as review artifacts: added/removed roles, score deltas, cluster drift, ordering changes.
4. **Prefer** explicit CHANGELOG entries and ontology version bumps when snapshots change.

Utilities: `evaluation/recommendation_diff.py`, `evaluation/evaluation_report.py`.

## Human-in-the-loop governance

- Operators approve roles in the review queue; approved state persists to disk.
- Explainability expanders surface why matched / why not / dimensions / diagnostics JSON.
- Ops logs emit `recommendation_hash`, `ontology_version`, and `benchmark_signature` after each generation run.
- Evaluation reports are suitable for release notes and architecture review packets.

## Planned evolution (`0.6.0-evaluation-layer`)

- Checked-in golden snapshots for public demo resume + feed (optional, reviewer-only).
- CLI entrypoint: `python -m evaluation.cli compare baseline.json current.json`.
- Dashboard tile for last `recommendation_hash` (read-only).
