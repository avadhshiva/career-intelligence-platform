# Drift monitoring

Reliability signals for a **deterministic** recommendation platform. Monitoring here means detectable, explainable change—not ML model drift.

## Deterministic output guarantees

| Guarantee | Verification |
|-----------|----------------|
| Stable ranking for fixed inputs | `test_deterministic_ranking_stable` |
| Regression JSON snapshots | `career_intelligence_engine/tests/test_regression.py` |
| Recommendation hash | `evaluation/recommendation_snapshot.recommendation_hash` |
| Ontology fingerprint | `career_intelligence_engine/ontology/version.get_ontology_version()` |

If `recommendation_hash` changes with identical resume + postings, investigate ontology edits, parser changes, or orchestration field normalization—not randomness.

## Benchmark drift categories

| Type | Example | Action |
|------|---------|--------|
| Adjacency contract | TPM expected in adjacent set but distance-only | Review eligibility matrix vs semantic distance |
| Cluster definition | `ai_program_management` in program top-4 | Update test cluster or document intentional promotion |
| Baseline score drift | `detect_drift` warnings | Regenerate `baseline_scores.json` only after approved ontology change |
| Contamination | Forbidden family in top-3 | Treat as high-severity; investigate scoring contamination rules |

Current known failures: [benchmark_drift_notes.md](benchmark_drift_notes.md).

## Stale ontology risks

- **Role family edits** change identity and match explanations without UI changes.
- **Dual engine copies** — platform embeds `career_agent_platform/career_intelligence_engine`; keep in sync with root `career_intelligence_engine` when developing ontology changes.
- **Ontology version** is a SHA-256 fingerprint of `role_families.py`, `capability_graph.py`, and `capability_vectors.py`.

Log field: `ontology_version=ontology-<12-char-hex>`.

## Recommendation consistency concerns

| Signal | Source | Interpretation |
|--------|--------|----------------|
| `recommendation_hash` | Ops log after generation | End-to-end ranking fingerprint |
| `benchmark_signature` | Ops log (informational) | Aggregate benchmark pass rate snapshot |
| Snapshot diff | `evaluation/recommendation_diff` | Per-job score/priority/cluster deltas |
| Session vs disk | Manual | Queue restore without canonical resume → Market/Cockpit gaps |

## Optional logging (enabled)

After each recommendation generation (`Job_Recommendations.py`):

```
event=recommendation_reliability_signals
  recommendation_hash='...'
  ontology_version='ontology-...'
  benchmark_signature='fixtures=N|adjacency_hits=X/Y|all_passed=...'
```

Configure verbosity: `CAREER_AGENT_LOG_LEVEL=DEBUG`.

## CI vs production

- **CI** fails on platform tests, engine tests (minus benchmark rankings), import smoke, and demo artifact generation.
- **Production** does not auto-fail on benchmark adjacency; operators use drift notes + signatures for release decisions.

## Related docs

- [evaluation_strategy.md](evaluation_strategy.md)
- [benchmark_drift_notes.md](benchmark_drift_notes.md)
- [operational_risks.md](operational_risks.md)
