# Persistence flow

## Storage locations (platform root)

| Artifact | Path | Purpose |
|----------|------|---------|
| Active resume marker | `data/active_resume.json` | Last `resume_id` for restart |
| Canonical resume | `data/resumes/{resume_id}.json` | Full text + `parsed_profile` + identity summary |
| Review queue | `applications/data/review_queue.json` | Pending/approved/rejected entries with embedded recommendation snapshots |
| Application packages | `applications/data/application_packages/` | Generated package JSON |
| Decision memory | `memory/data/` (if initialized) | Human decision audit |
| Match postings cache | `workflow_session` / session keys | JD text used for re-run |

All paths are **gitignored** for user JSON except committed sample feeds.

## Canonical resume persistence

1. `build_canonical_resume()` serializes `CandidateProfile` into `parsed_profile`.
2. `persist_and_activate_canonical_resume()` writes `{resume_id}.json` and updates `active_resume.json`.
3. `CanonicalResumeStore.load()` auto-migrates legacy identity-only files on read.

**Restart rule:** Session `active_resume_id` is optional; `load_active_resume_id()` from disk is authoritative when the session key is absent.

## Review queue lifecycle

1. `ReviewQueueManager.initialize()` ensures file exists, scrubs listing URL cache fields, runs `_repair_persisted_queue()`.
2. `enqueue_many()` appends entries with full `recommendation` dict snapshots.
3. Approve/reject transitions update `state` and timestamps in-place.
4. On fresh Streamlit session, `_init_session()` rebuilds `st.session_state.recommendations` from valid queue rows (`RecommendationResult.from_dict`).

Queue is the **source of truth** for approval status across restarts; in-memory rec list can be stale until `_sync_recommendations_from_queue` runs.

## Package lifecycle

1. User approves on Recommendations → queue state `approved`.
2. Application workspace calls `ApplicationPackageBuilder.build(..., persist=True)`.
3. `ApplicationReviewManager.save_package()` writes under `application_packages/`.
4. `selected_package_id` / `active_package_id` session keys select UI tab content.

## Profile restore sources (after restart)

| Source | When used |
|--------|-----------|
| `session` | `st.session_state.career_profile` already set in-tab |
| `canonical_disk` | Session empty; `active_resume.json` + `data/resumes/{id}.json` with valid `parsed_profile` |
| `none` | No marker or corrupt profile → Market/Cockpit prompt user to re-run recommendations |

Logged as `profile_restore` with `source=` field.

## Hygiene hooks

- `state_hygiene.safe_cleanup_demo_state()` — one-time demo/sample purge flags.
- `purge_demo_entries()` — removes preview/sample queue rows.
- `repair_queue_store()` — drops null/malformed queue rows on load.

## Backward compatibility

- Legacy `ResumeIdentity`-only JSON files migrate to `CanonicalResume` on load.
- Queue entries without `recommendation` payload are skipped during restore (silent skip).
