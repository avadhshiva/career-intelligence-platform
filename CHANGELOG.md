# Changelog

All notable engineering milestones for the Job Intelligence platform. Versioning follows semantic intent; scoring logic changes require explicit review.

## [0.5.1] — 2026-05-31

### Added

- MIT `LICENSE` at repository root.
- `FINAL_RELEASE_CHECKLIST.md` — publication gate evidence.

### Changed

- Documentation and README release labels normalized to `0.5.1` (application `version.py` unchanged per feature-freeze scope).

---

## [0.5.1-release-candidate] — 2026-05-28

### Added

- Golden recommendation snapshots under `career_agent_platform/evaluation/golden/` (TPM, delivery leadership, platform engineering).
- `tests/test_golden_recommendations.py` — hash regression with readable diff via `recommendation_diff.py`.
- Read-only demo mode (`CAREER_AGENT_DEMO_MODE=1`) — blocks review queue, resume, and package persistence writes.
- Recommendation governance panel (hash, ontology version, benchmark signature, deterministic mode).
- `docs/golden_snapshot_policy.md`, `docs/release_candidate_checklist.md`.
- CI: golden tests, demo-mode smoke, repo hygiene guard for runtime JSON.

### Unchanged

- Deterministic scoring and ranking algorithms.
- Benchmark fixture expectations (informational drift notes remain).

---

## [0.6.0-evaluation-layer] — planned

### Added

- GitHub Actions `ci.yml` — platform tests, engine tests (benchmark drift excluded), demo artifact validation, import smoke.
- `career_agent_platform/evaluation/` — snapshot, diff, and report utilities.
- Recommendation governance diagnostics in `match_detail.diagnostics`.
- Reliability ops signals: `recommendation_hash`, `ontology_version`, `benchmark_signature`.
- Documentation: `docs/evaluation_strategy.md`, `docs/drift_monitoring.md`.

### Unchanged

- Deterministic scoring and ranking algorithms.
- Benchmark fixture expectations (4 known failures remain informational).

---

## [0.5.0-stabilized] — 2026-05-28

### Added

- Structured ops logging (`career_agent.ops`) for generation, persistence, and restore.
- Public-repo polish: README, architecture docs, Mermaid diagrams, developer guide.
- Sanitized public demo artifacts under `career_agent_platform/demo/public/`.
- `docs/benchmark_drift_notes.md` capturing four non-blocking benchmark failures.

### Fixed

- Persistence lifecycle: canonical resume, review queue restore, restart recovery.
- State hygiene and queue validation for trusted workflow paths.
- Demo/sample data resurrection guards.

### Known issues

- Benchmark adjacency: `program_leadership_enterprise`, `cloud_transformation_lead` (2 fixtures).
- Benchmark aggregate: `adjacency_hits=23/25`.
- Program cluster test: `ai_program_management` in calibration top-4.
- See [docs/benchmark_drift_notes.md](docs/benchmark_drift_notes.md).

---

## Earlier phases

Pre-0.5.0 work established the deterministic engine, Streamlit multipage app, application packages, and market intelligence surfaces. Refer to git history and `docs/recommendation_lifecycle.md` for feature chronology.
