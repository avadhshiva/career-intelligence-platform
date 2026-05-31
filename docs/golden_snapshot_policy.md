# Golden snapshot policy

Committed golden recommendation snapshots live under `career_agent_platform/evaluation/golden/`. They protect deterministic ranking outputs without changing scoring logic.

## Fixtures

| Fixture ID | Resume source | Intent |
|------------|---------------|--------|
| `tpm_sample` | `RESUME_TPM` (calibration) | Technical program management |
| `delivery_leadership_sample` | `RESUME_PROGRAM_DIRECTOR` | Program / delivery leadership |
| `platform_engineering_sample` | `RESUME_ENGINEERING_MANAGER` | Platform / engineering management |

All fixtures use the shared job feed `career_agent_platform/data/sample_job_feed.json`.

## Approval workflow

1. Make an intentional change (ontology, normalization, or approved ranking fix).
2. Regenerate snapshots from `career_agent_platform/`:
   ```powershell
   $env:PYTHONPATH = (Get-Location).Path
   python evaluation/golden/generate_golden_snapshots.py
   ```
3. Review `manifest.json` hash changes and spot-check `recommendation_diff` output if needed.
4. Run `pytest tests/test_golden_recommendations.py -v`.
5. Commit golden JSON + manifest with the PR that explains **why** hashes changed.

Reviewers should not approve golden updates without a linked rationale (ontology bump, bug fix, or documented fixture change).

## Expected drift handling

| Signal | Action |
|--------|--------|
| `recommendation_hash` unchanged | CI passes; no golden update |
| Hash changed, diff shows score/priority/order deltas | Fail CI until golden regen + review |
| `ontology_version` changed, hash unchanged | Informational only (ontology tracked on snapshot, not in hash) |
| `ontology_version` changed, hash changed | Regenerate golden after ontology review |

Tests fail **only** on meaningful deterministic drift (hash mismatch). Diff output uses `evaluation/recommendation_diff.py` and `format_report_text` for readable CI logs.

## Ontology version interaction

`get_ontology_version()` fingerprints role-family and capability graph modules. Ontology edits may change rankings; golden hashes encode job order, scores, priorities, and primary role families — not free-text fields.

When bumping ontology:

1. Note the new `ontology_version` in the PR.
2. Regenerate golden snapshots in the same commit.
3. Cross-check engine benchmark snapshots separately (`career_intelligence_engine/benchmarks/snapshots/`) if adjacency expectations shift.

## Reviewer workflow

- Use `CAREER_AGENT_DEMO_MODE=1` for read-only exploration (see release candidate checklist).
- Compare live **Recommendation governance** panel hash to golden `manifest.json` for a fixture after local generation.
- Do not hand-edit golden JSON; always use `generate_golden_snapshots.py`.
