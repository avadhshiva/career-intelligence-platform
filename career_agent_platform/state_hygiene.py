"""Data integrity + state hygiene helpers for UI-facing state.

This module is intentionally strict: anything that smells like a placeholder,
preview/demo seed, or incomplete record is excluded from UI dropdowns and counts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from application_tracking.models import ApplicationRecord
from application_tracking.tracker import ApplicationTracker
from application_workspace.models import ApplicationPackage
from application_workspace.review_manager import ApplicationReviewManager
from presentation.sanitize import is_placeholder_text, sanitize_display_text
from review_queue_manager import ReviewQueueManager, QueueState
from queue_validation import is_valid_queue_entry


_BAD_LABELS = frozenset(
    {
        "--",
        "role",
        "company",
        "role @ company",
    }
)

_BAD_PREFIXES: tuple[str, ...] = (
    "tmp",
    "sample_",
    "preview_",
)


def is_valid_display_value(value: str | None) -> bool:
    """True only when the value is safe to show in UI (no placeholders)."""
    if value is None:
        return False
    raw = str(value).strip()
    if is_placeholder_text(raw):
        return False
    cleaned = sanitize_display_text(raw)
    if not cleaned:
        return False
    low = cleaned.strip().lower()
    if low in _BAD_LABELS:
        return False
    for p in _BAD_PREFIXES:
        if low.startswith(p):
            return False
    if "@" in low and low.replace(" ", "") == "role@company":
        return False
    return True


def is_valid_job_identity(*, job_title: str | None, company: str | None) -> bool:
    return is_valid_display_value(job_title) and is_valid_display_value(company)


def is_valid_job_id(job_id: str | None) -> bool:
    if not job_id:
        return False
    low = str(job_id).strip().lower()
    if not low:
        return False
    for p in _BAD_PREFIXES:
        if low.startswith(p):
            return False
    return True


def _has_recommendation_snapshot(snapshot: dict | None) -> bool:
    snap = snapshot or {}
    if not isinstance(snap, dict):
        return False
    if not snap:
        return False
    # Minimal “exists” requirement: must have at least a score/brief signal.
    return any(k in snap for k in ("overall_match", "match_detail", "why_matched", "why_not_matched"))


def is_actionable_queue_entry(entry: dict[str, Any] | None) -> bool:
    """Action buttons must only render for safe, current, user entries."""
    if not entry or not isinstance(entry, dict):
        return False
    if ReviewQueueManager.is_demo_entry(entry):
        return False
    entry_id = str(entry.get("entry_id") or "").strip()
    if not entry_id:
        return False
    rec = entry.get("recommendation") or {}
    if not isinstance(rec, dict) or not rec:
        return False
    job_id = str(entry.get("job_id") or rec.get("job_id") or "").strip()
    if not is_valid_job_id(job_id):
        return False
    if not _has_recommendation_snapshot(rec):
        return False
    # Respect explicit purge/invalid markers if present.
    if bool(entry.get("purged")) or bool(entry.get("stale")):
        return False
    return True


def is_valid_package(pkg: ApplicationPackage) -> bool:
    if not is_valid_job_id(pkg.source_job_id):
        return False
    if not is_valid_job_identity(job_title=pkg.job_title, company=pkg.company):
        return False
    if not _has_recommendation_snapshot(pkg.recommendation_snapshot):
        return False
    # Must be more than a blank shell: either has artifacts or meaningful state history/notes.
    has_artifacts = bool(pkg.tailored_resume_text.strip()) or bool(pkg.cover_letter) or bool(pkg.recruiter_message) or bool(pkg.interview_prep) or bool(pkg.artifacts)
    has_state = bool(pkg.state_history) or bool(pkg.approval_status)
    return has_artifacts or has_state


def is_valid_tracker_record(rec: ApplicationRecord) -> bool:
    if not is_valid_job_id(rec.job_id):
        return False
    if not is_valid_job_identity(job_title=rec.role, company=rec.company):
        return False
    return _has_recommendation_snapshot(rec.recommendation_snapshot)


def _unique_by_job_id(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for r in rows:
        job_id = str(r.get("job_id") or "")
        if not job_id:
            continue
        prev = latest.get(job_id)
        if prev is None or (r.get("updated_at") or "") >= (prev.get("updated_at") or ""):
            latest[job_id] = r
    return list(latest.values())


@dataclass(frozen=True)
class QueueView:
    pending: list[dict[str, Any]]
    approved: list[dict[str, Any]]
    rejected: list[dict[str, Any]]


def get_valid_queue_entries(queue: ReviewQueueManager) -> QueueView:
    pending = [e for e in queue.list_by_state(QueueState.PENDING_REVIEW) if is_valid_queue_entry(e)]
    approved = [e for e in queue.list_by_state(QueueState.APPROVED) if is_valid_queue_entry(e)]
    rejected = [e for e in queue.list_by_state(QueueState.REJECTED) if is_valid_queue_entry(e)]
    return QueueView(
        pending=_unique_by_job_id(pending),
        approved=_unique_by_job_id(approved),
        rejected=_unique_by_job_id(rejected),
    )


def get_valid_packages(review_mgr: ApplicationReviewManager) -> list[ApplicationPackage]:
    packages: list[ApplicationPackage] = []
    for row in review_mgr.list_packages():
        pkg_id = str(row.get("package_id") or "")
        if not pkg_id:
            continue
        try:
            pkg = review_mgr.get_package(pkg_id)
        except KeyError:
            continue
        if is_valid_package(pkg):
            packages.append(pkg)
    return packages


def get_valid_tracker_records(tracker: ApplicationTracker) -> list[ApplicationRecord]:
    return [r for r in tracker.list_all() if is_valid_tracker_record(r)]


def get_valid_tracker_records_for_packages(
    tracker: ApplicationTracker,
    *,
    valid_package_ids: set[str],
) -> list[ApplicationRecord]:
    """Tracker rows must reconcile with the same valid package universe."""
    if not valid_package_ids:
        return []
    return [
        r
        for r in get_valid_tracker_records(tracker)
        if str(r.package_id or "") in valid_package_ids
    ]


def safe_cleanup_demo_state(*, data_root: Path | None = None) -> dict[str, int]:
    """One-time cleanup of persisted placeholder/demo state.

    Purges queue entries, packages (index + package json), tracker rows, and decision memory rows
    that are clearly demo/placeholder (tmp*/sample*/preview* or invalid labels).
    """
    platform_root = Path(__file__).resolve().parent
    root = data_root or (platform_root / "applications" / "data")

    removed: dict[str, int] = {"queue": 0, "packages": 0, "tracker": 0, "decision_memory": 0}

    # Queue cleanup (reuse manager but extend beyond sample_ to tmp* via our validators)
    queue_mgr = ReviewQueueManager(data_dir=root)
    store = queue_mgr._load()  # noqa: SLF001 (internal but deterministic)
    before = len(store.get("entries") or [])
    store["entries"] = [e for e in (store.get("entries") or []) if is_valid_queue_entry(e)]
    removed["queue"] = before - len(store["entries"])
    if removed["queue"]:
        queue_mgr._save(store)  # noqa: SLF001

    # Packages cleanup
    pkg_root = root / "application_packages"
    review_mgr = ApplicationReviewManager(data_dir=pkg_root)
    index = review_mgr._load_index()  # noqa: SLF001
    kept_rows: list[dict[str, Any]] = []
    deleted_ids: list[str] = []
    for row in index.get("packages") or []:
        pkg_id = str(row.get("package_id") or "")
        if not pkg_id:
            continue
        try:
            pkg = review_mgr.get_package(pkg_id)
        except KeyError:
            deleted_ids.append(pkg_id)
            continue
        if is_valid_package(pkg):
            kept_rows.append(row)
        else:
            deleted_ids.append(pkg_id)
    if deleted_ids:
        for pkg_id in deleted_ids:
            p = pkg_root / f"{pkg_id}.json"
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
        index["packages"] = kept_rows
        review_mgr._save_index(index)  # noqa: SLF001
    removed["packages"] = len(deleted_ids)
    kept_pkg_ids = {str(r.get("package_id") or "") for r in kept_rows if r.get("package_id")}

    # Tracker cleanup
    tracker = ApplicationTracker(data_dir=root / "application_tracking")
    tstore = tracker._load()  # noqa: SLF001
    apps = tstore.get("applications") or []
    before_t = len(apps)
    kept = []
    for row in apps:
        try:
            rec = ApplicationRecord.from_dict(row)
        except Exception:
            continue
        if is_valid_tracker_record(rec) and (not kept_pkg_ids or rec.package_id in kept_pkg_ids):
            kept.append(row)
    tstore["applications"] = kept
    removed["tracker"] = before_t - len(kept)
    if removed["tracker"]:
        tracker._save(tstore)  # noqa: SLF001

    # Decision memory cleanup
    mem_path = root / "decision_memory.json"
    if mem_path.exists():
        import json

        try:
            mem = json.loads(mem_path.read_text(encoding="utf-8"))
        except Exception:
            mem = {}
        rows = mem.get("decisions") or []
        before_m = len(rows)
        mem["decisions"] = [
            d
            for d in rows
            if is_valid_job_id(str(d.get("job_id") or ""))
            and is_valid_job_identity(job_title=d.get("job_title"), company=d.get("company"))
        ]
        removed["decision_memory"] = before_m - len(mem["decisions"])
        if removed["decision_memory"]:
            mem_path.write_text(json.dumps(mem, indent=2), encoding="utf-8")

    return removed

