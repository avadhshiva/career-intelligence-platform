# Ontology Freeze Policy

The role-family ontology, capability vectors, and calibration penalties are **stable infrastructure**.

## Do not change without cause

Avoid arbitrary tuning of penalties, vectors, or eligibility gates.

## Recalibrate only when

1. **Benchmark contamination** — real-world or synthetic benchmarks show cross-family inflation.
2. **Regression drift** — regression snapshots fail (primary flip, exclusion breach, contamination spike).
3. **Confidence instability** — confidence calibration drops across the fixture suite.

## Evaluation-first workflow

1. Run `python -m career_intelligence_engine.benchmarks.run`
2. Run `python -m career_intelligence_engine.benchmarks.run_real_world`
3. Compare regression snapshots (`--check-regression`)
4. Document any ontology change with benchmark before/after metrics
