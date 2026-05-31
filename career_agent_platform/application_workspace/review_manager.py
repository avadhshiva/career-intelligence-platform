"""Human approval workflow with deterministic lifecycle state machine."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from application_workspace.models import (
    ApplicationApprovalState,
    ApplicationPackage,
    StateHistoryEntry,
    utc_now_iso,
)
from application_workspace.state_machine import (
    TransitionResult,
    allowed_targets,
    can_transition,
    transition_warning,
)


def _platform_root() -> Path:
    return Path(__file__).resolve().parents[1]


class ApplicationReviewManager:
    """Persist application packages under applications/data/application_packages/."""

    def __init__(self, data_dir: Path | None = None, tracker: Any | None = None) -> None:
        root = data_dir or (_platform_root() / "applications" / "data" / "application_packages")
        self._root = root
        self._index_path = root / "index.json"
        self._tracker = tracker

    def initialize(self) -> None:
        from demo_mode import persistence_writes_enabled

        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "exports").mkdir(parents=True, exist_ok=True)
        if not persistence_writes_enabled():
            return
        if not self._index_path.exists():
            self._index_path.write_text(
                json.dumps({"packages": []}, indent=2),
                encoding="utf-8",
            )

    def _package_path(self, package_id: str) -> Path:
        return self._root / f"{package_id}.json"

    def _load_index(self) -> dict[str, Any]:
        self.initialize()
        return json.loads(self._index_path.read_text(encoding="utf-8"))

    def _save_index(self, data: dict[str, Any]) -> None:
        from demo_mode import persistence_writes_enabled

        if not persistence_writes_enabled():
            return
        self._index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_allowed_actions(self, package_id: str) -> list[str]:
        pkg = self.get_package(package_id)
        return sorted(s.value for s in allowed_targets(pkg.approval_status))

    def save_package(self, package: ApplicationPackage) -> str:
        from demo_mode import persistence_writes_enabled

        self.initialize()
        path = self._package_path(package.package_id)
        if not persistence_writes_enabled():
            return str(path)
        path.write_text(json.dumps(package.to_dict(), indent=2), encoding="utf-8")
        index = self._load_index()
        row = {
            "package_id": package.package_id,
            "source_job_id": package.source_job_id,
            "job_title": package.job_title,
            "company": package.company,
            "approval_status": package.approval_status.value,
            "generated_at": package.generated_at,
            "overall_quality": (
                package.quality_scores.overall_application_quality_score
                if package.quality_scores
                else 0.0
            ),
        }
        existing = [p for p in index["packages"] if p["package_id"] != package.package_id]
        existing.append(row)
        index["packages"] = sorted(existing, key=lambda x: x.get("generated_at", ""), reverse=True)
        self._save_index(index)
        self._sync_tracker(package)
        return package.package_id

    def _sync_tracker(self, package: ApplicationPackage) -> None:
        try:
            from application_tracking.tracker import ApplicationTracker

            tracker = self._tracker if self._tracker is not None else ApplicationTracker()
            tracker.sync_from_package(package)
        except Exception:
            pass

    def create_package_id(self) -> str:
        return str(uuid.uuid4())

    def get_package(self, package_id: str) -> ApplicationPackage:
        path = self._package_path(package_id)
        if not path.exists():
            raise KeyError(f"package_id not found: {package_id}")
        return ApplicationPackage.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_packages(
        self,
        status: ApplicationApprovalState | None = None,
    ) -> list[dict[str, Any]]:
        index = self._load_index()
        rows = index.get("packages") or []
        if status is None:
            return rows
        return [r for r in rows if r.get("approval_status") == status.value]

    def record_initial_state(self, package: ApplicationPackage) -> ApplicationPackage:
        if not package.state_history:
            package.state_history.append(
                StateHistoryEntry(
                    from_state="created",
                    to_state=ApplicationApprovalState.GENERATED.value,
                    timestamp=package.generated_at or utc_now_iso(),
                    reviewer_action_reason="package_created",
                    review_notes="Application package generated.",
                    success=True,
                ),
            )
        return package

    def _append_history(
        self,
        pkg: ApplicationPackage,
        *,
        from_state: ApplicationApprovalState,
        to_state: ApplicationApprovalState,
        success: bool,
        notes: str = "",
        reason: str = "",
        warning: str = "",
    ) -> None:
        pkg.state_history.append(
            StateHistoryEntry(
                from_state=from_state.value,
                to_state=to_state.value,
                timestamp=utc_now_iso(),
                review_notes=notes,
                reviewer_action_reason=reason,
                success=success,
                warning=warning,
            ),
        )

    def transition(
        self,
        package_id: str,
        new_state: ApplicationApprovalState,
        *,
        notes: str = "",
        reason: str = "",
    ) -> TransitionResult:
        """Apply lifecycle transition; never raises on invalid moves."""
        pkg = self.get_package(package_id)
        current = pkg.approval_status

        if current == new_state:
            return TransitionResult(
                success=True,
                package_id=package_id,
                from_state=current,
                to_state=new_state,
                message=f"Already in state '{new_state.value}'.",
            )

        if not can_transition(current, new_state):
            warning = transition_warning(current, new_state)
            pkg.last_warning = warning
            self._append_history(
                pkg,
                from_state=current,
                to_state=current,
                success=False,
                notes=notes,
                reason=reason or "invalid_transition",
                warning=warning,
            )
            self.save_package(pkg)
            return TransitionResult(
                success=False,
                package_id=package_id,
                from_state=current,
                to_state=current,
                warning=warning,
            )

        pkg.approval_status = new_state
        if notes:
            pkg.reviewer_notes = notes
        if reason and new_state == ApplicationApprovalState.REJECTED:
            pkg.rejection_reason = reason
        pkg.last_warning = ""
        self._append_history(
            pkg,
            from_state=current,
            to_state=new_state,
            success=True,
            notes=notes,
            reason=reason or f"transition_to_{new_state.value}",
        )
        self.save_package(pkg)
        return TransitionResult(
            success=True,
            package_id=package_id,
            from_state=current,
            to_state=new_state,
            message=f"Transitioned from '{current.value}' to '{new_state.value}'.",
        )

    def mark_under_review(self, package_id: str, notes: str = "") -> TransitionResult:
        return self.transition(
            package_id,
            ApplicationApprovalState.UNDER_REVIEW,
            notes=notes,
            reason="mark_under_review",
        )

    def approve(self, package_id: str, notes: str = "") -> TransitionResult:
        return self.transition(
            package_id,
            ApplicationApprovalState.APPROVED,
            notes=notes,
            reason="approve_package",
        )

    def reject(self, package_id: str, reason: str = "", notes: str = "") -> TransitionResult:
        return self.transition(
            package_id,
            ApplicationApprovalState.REJECTED,
            notes=notes,
            reason=reason or "reject_package",
        )

    def mark_exported(self, package_id: str, notes: str = "") -> TransitionResult:
        return self.transition(
            package_id,
            ApplicationApprovalState.EXPORTED,
            notes=notes,
            reason="export_package",
        )

    def reopen(self, package_id: str, notes: str = "") -> TransitionResult:
        return self.transition(
            package_id,
            ApplicationApprovalState.REOPENED,
            notes=notes,
            reason="reopen_package",
        )

    def archive(self, package_id: str, notes: str = "") -> TransitionResult:
        return self.transition(
            package_id,
            ApplicationApprovalState.ARCHIVED,
            notes=notes,
            reason="archive_package",
        )

    def update_package(self, package: ApplicationPackage) -> ApplicationPackage:
        self.save_package(package)
        return package
