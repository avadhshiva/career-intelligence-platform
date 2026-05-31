"""Compare two recommendation snapshots without altering scoring logic."""

from __future__ import annotations

from typing import Any


def _index_by_job(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(i["job_id"]): i for i in items if i.get("job_id")}


def diff_snapshots(
    baseline: dict[str, Any] | list[dict[str, Any]],
    current: dict[str, Any] | list[dict[str, Any]],
) -> dict[str, Any]:
    """Diff normalized snapshot payloads or item lists."""
    if isinstance(baseline, dict):
        base_items = list(baseline.get("items") or [])
        cur_items = list(current.get("items") or []) if isinstance(current, dict) else list(current)
        meta = {
            "baseline_hash": baseline.get("recommendation_hash"),
            "current_hash": current.get("recommendation_hash") if isinstance(current, dict) else None,
            "ontology_version_baseline": baseline.get("ontology_version"),
            "ontology_version_current": current.get("ontology_version") if isinstance(current, dict) else None,
        }
    else:
        base_items = list(baseline)
        cur_items = list(current)
        meta = {}

    base_by_id = _index_by_job(base_items)
    cur_by_id = _index_by_job(cur_items)

    base_ids = set(base_by_id)
    cur_ids = set(cur_by_id)

    added = sorted(cur_ids - base_ids)
    removed = sorted(base_ids - cur_ids)

    score_deltas: list[dict[str, Any]] = []
    priority_changes: list[dict[str, Any]] = []
    cluster_drift: list[dict[str, Any]] = []

    for job_id in sorted(base_ids & cur_ids):
        b = base_by_id[job_id]
        c = cur_by_id[job_id]
        delta = round(float(c["overall_match"]) - float(b["overall_match"]), 6)
        if delta != 0.0:
            score_deltas.append(
                {
                    "job_id": job_id,
                    "baseline_score": b["overall_match"],
                    "current_score": c["overall_match"],
                    "delta": delta,
                },
            )
        if b.get("recommendation_priority") != c.get("recommendation_priority"):
            priority_changes.append(
                {
                    "job_id": job_id,
                    "baseline_priority": b.get("recommendation_priority"),
                    "current_priority": c.get("recommendation_priority"),
                },
            )
        if b.get("role_cluster") != c.get("role_cluster") or b.get("primary_role_family") != c.get(
            "primary_role_family",
        ):
            cluster_drift.append(
                {
                    "job_id": job_id,
                    "baseline_cluster": b.get("role_cluster") or b.get("primary_role_family"),
                    "current_cluster": c.get("role_cluster") or c.get("primary_role_family"),
                },
            )

    base_order = [i["job_id"] for i in base_items]
    cur_order = [i["job_id"] for i in cur_items]
    ordering_changes: list[dict[str, Any]] = []
    if base_order != cur_order:
        ordering_changes.append(
            {
                "baseline_order": base_order,
                "current_order": cur_order,
            },
        )

    return {
        **meta,
        "added_roles": added,
        "removed_roles": removed,
        "score_deltas": score_deltas,
        "priority_changes": priority_changes,
        "cluster_drift": cluster_drift,
        "ordering_changes": ordering_changes,
        "unchanged_count": len(base_ids & cur_ids) - len(score_deltas) - len(priority_changes),
        "has_changes": bool(
            added
            or removed
            or score_deltas
            or priority_changes
            or cluster_drift
            or ordering_changes,
        ),
    }
