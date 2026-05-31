# Operational safety review (document-only)

Risks identified during post-stabilization hardening. **Not fixed** in this phase unless marked critical.

## Silent failure zones

| Zone | Behavior | Impact |
|------|----------|--------|
| Canonical persist exception | Caught in Recommendations; UI warning shown | Recs work in-session; Market/Cockpit empty after restart |
| Queue row `from_dict` failure | `continue` in restore loop | Missing card for that job_id with no user-visible error |
| Profile `model_validate` failure | Bare `except` in `_init_session` / Market page | Profile stays `None`; downstream pages show info banner only |
| Legacy resume migration | `except: pass` in `CanonicalResumeStore.load` | Stale file shape may load without migration |
| Package build errors | Workspace may surface Streamlit error if uncaught | Partial session state if rerun interrupted |

## Shared-path persistence risks

| Risk | Detail |
|------|--------|
| Single queue file | `review_queue.json` — concurrent Streamlit tabs can race last-write-wins |
| Shared `data/resumes/` | Same `resume_id` hash for identical text — overwrites without prompt |
| `active_resume.json` | Global marker — last upload wins across profiles |
| Listing URL scrub | Mutates queue-related JSON on every `initialize()` |

## Stale state risks

| Risk | Detail |
|------|--------|
| Session vs queue | In-memory `recommendations` can diverge until `_sync_recommendations_from_queue` |
| Match postings | JD cache session-only; refine re-run may use outdated postings if not re-stored |
| `entry_map` | Orphaned if queue repaired but session not cleared |
| Demo purge flag | `demo_queue_purged` once per session — won't re-purge if demo reintroduced |

## Backward compatibility risks

| Risk | Detail |
|------|--------|
| Queue schema drift | Older entries missing `recommendation` blob are skipped on restore |
| Identity-only resume JSON | Auto-migration on read; failure leaves partial canonical |
| Embedded vs root engine | Two copies of `career_intelligence_engine` — PYTHONPATH determines which runs |

## Restart consistency risks

| Risk | Detail |
|------|--------|
| Profile without queue | Possible if marker + canonical exist but queue cleared |
| Queue without profile | Possible if persist failed but enqueue succeeded |
| Market page | Depends on profile chain; queue-only restore insufficient |
| Package index vs tracker | Dashboard counts require both package files and tracker init |

## Criticality assessment

No **P0 production outage** class issues identified for a local-first Streamlit tool. Highest user-visible risk remains **canonical persist failure** → post-restart Market/Cockpit degradation (mitigated by UI warning on failure).

## Recommended monitoring (local)

Use `CAREER_AGENT_LOG_LEVEL=DEBUG` and watch for:

- `canonical_resume_persist_failed`
- `queue_restore` with `restored_count=0` but non-zero `entry_count`
- `profile_restore` with `source=none`
