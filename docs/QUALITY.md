# Quality signals

Engineering maturity indicators for reviewers (no scoring logic changes).

## Versioning

- **Package version:** `career_agent_platform/version.py` → `__version__` (runtime caption; docs/release label: `0.5.1`)
- **Logged at startup:** `app_startup` and `ops_logging_ready` include version + release label

## Determinism

- Ranking and matching use fixed ontology pipelines—**no random seed** in the recommendation path.
- Re-running the same inputs in the same code version yields the same scores.
- Documented in `DETERMINISM_NOTE` inside `version.py` and shown in the Home page expander.

## Test baselines (last verified)

| Suite | Result |
|-------|--------|
| `career_agent_platform/tests` | 95 passed |
| `career_intelligence_engine/tests` | 141 passed, 4 failed |

## Benchmark drift (intentionally open)

Four engine tests fail on **adjacency / top-ranking expectations**, not primary classification:

- See [benchmark_drift_notes.md](benchmark_drift_notes.md)
- Classified as heuristic evolution vs stale test contracts
- **Not fixed** during stabilization/polish phases to avoid unintended scoring changes

## Observability

- Logger: `career_agent.ops`
- Env: `CAREER_AGENT_LOG_LEVEL`
- Events cover generation, persistence, restore, packages

## Public demo safety

- `demo/public/*` generated from fictional resume text only
- Regenerate via `python demo/generate_public_snapshots.py` after engine changes
