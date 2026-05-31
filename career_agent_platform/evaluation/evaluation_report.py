"""Human-readable evaluation reports from snapshot diffs."""

from __future__ import annotations

from typing import Any

from evaluation.recommendation_diff import diff_snapshots


def build_evaluation_report(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    """Structured report for governance and regression review."""
    diff = diff_snapshots(baseline, current)
    return {
        "summary": {
            "has_changes": diff["has_changes"],
            "added_count": len(diff["added_roles"]),
            "removed_count": len(diff["removed_roles"]),
            "score_delta_count": len(diff["score_deltas"]),
            "priority_change_count": len(diff["priority_changes"]),
            "cluster_drift_count": len(diff["cluster_drift"]),
            "ordering_changed": bool(diff["ordering_changes"]),
            "recommendation_hash_changed": baseline.get("recommendation_hash")
            != current.get("recommendation_hash"),
            "ontology_version_changed": baseline.get("ontology_version")
            != current.get("ontology_version"),
        },
        "diff": diff,
        "baseline": {
            "snapshot_id": baseline.get("snapshot_id"),
            "created_at": baseline.get("created_at"),
            "recommendation_hash": baseline.get("recommendation_hash"),
        },
        "current": {
            "snapshot_id": current.get("snapshot_id"),
            "created_at": current.get("created_at"),
            "recommendation_hash": current.get("recommendation_hash"),
        },
    }


def format_report_text(report: dict[str, Any]) -> str:
    """Plain-text report for CLI logs and CI artifacts."""
    summary = report.get("summary") or {}
    diff = report.get("diff") or {}
    lines = [
        "=== Recommendation evaluation report ===",
        f"Has changes: {summary.get('has_changes')}",
        f"Added roles: {summary.get('added_count', 0)}",
        f"Removed roles: {summary.get('removed_count', 0)}",
        f"Score deltas: {summary.get('score_delta_count', 0)}",
        f"Priority changes: {summary.get('priority_change_count', 0)}",
        f"Cluster drift: {summary.get('cluster_drift_count', 0)}",
        f"Ordering changed: {summary.get('ordering_changed')}",
        f"Recommendation hash changed: {summary.get('recommendation_hash_changed')}",
        f"Ontology version changed: {summary.get('ontology_version_changed')}",
    ]
    if diff.get("added_roles"):
        lines.append(f"Added: {', '.join(diff['added_roles'])}")
    if diff.get("removed_roles"):
        lines.append(f"Removed: {', '.join(diff['removed_roles'])}")
    for item in diff.get("score_deltas") or []:
        lines.append(
            f"  score {item['job_id']}: {item['baseline_score']} -> {item['current_score']} "
            f"(delta {item['delta']:+.4f})",
        )
    for item in diff.get("priority_changes") or []:
        lines.append(
            f"  priority {item['job_id']}: {item['baseline_priority']} -> {item['current_priority']}",
        )
    for item in diff.get("cluster_drift") or []:
        lines.append(
            f"  cluster {item['job_id']}: {item['baseline_cluster']} -> {item['current_cluster']}",
        )
    if diff.get("ordering_changes"):
        oc = diff["ordering_changes"][0]
        lines.append(f"  order baseline: {oc.get('baseline_order')}")
        lines.append(f"  order current:  {oc.get('current_order')}")
    return "\n".join(lines)
