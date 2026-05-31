# Recommendation lifecycle

## End-to-end flow

```
Resume + JDs
    → RecommendationEngine.recommend_from_resume()
    → enrich_recommendations()
    → session: career_profile, recommendations, entry_map
    → persist canonical resume (disk)
    → ReviewQueueManager.enqueue_many() (disk)
    → UI cards + approve/reject
    → (approved) Application workspace → package build
```

## Generation phase

1. **Inputs**: Effective resume text (upload or paste) + one or more job postings (`GenericJobParser`).
2. **Engine**: Produces `CandidateProfile` and `list[RecommendationResult]` — deterministic, no LLM in default path.
3. **Enrichment**: `intelligence_enrichment.enrich_recommendations()` adds presentation fields (no score changes).
4. **Session update**: `career_profile`, `recommendations`, `store_match_postings()` for refine/re-run.
5. **Persistence**: Canonical resume save (required for post-restart Market/Cockpit).
6. **Queue**: Each rec gets `entry_id`; `entry_map[job_id] = entry_id`.

Ops logs: `recommendation_generation_start|end` with `elapsed_ms`, `posting_count`, `result_count`.

## Review phase

- **Pending**: Default after enqueue.
- **Approved**: Unlocks Application workspace package generation.
- **Rejected**: Optional `rejection_reason`; card hidden or filtered per UI rules.
- **Applied / Archived**: Lifecycle extensions for tracking dashboard.

`_sync_recommendations_from_queue()` merges persisted queue state into in-memory `ApprovalStatus` on each Recommendations page load.

## Restart recovery

| Component | Recovery behavior |
|-----------|---------------------|
| Recommendations list | Rebuilt from queue JSON if session empty |
| `entry_map` | Restored from queue `entry_id` / `job_id` pairs |
| `career_profile` | Restored from canonical disk if session empty |
| Match postings | Session-only unless re-ingested |
| Market snapshot | Recomputed from profile when page loads |

Ops logs: `queue_restore` with `restored_count`, `entry_count`; `profile_restore` with `source`.

## Refine analysis (no full re-onboarding)

User can replace resume or JDs and **Re-run scoring** using cached postings from `workflow_session`. Does not automatically re-persist canonical resume unless generation path runs again.

## Package handoff

Approved `RecommendationResult` snapshot in queue row is the contract for `ApplicationPackageBuilder`. Package stores its own `recommendation_snapshot` copy at build time.

Ops logs: `package_generation_start|end|failed` with `job_id`, `package_id`, `persist`.

## Explicit non-goals

- No automatic re-ranking from human feedback (offline learning is roadmap-only).
- No modification to `BenchmarkEvaluator` or ontology weights in platform layer.
