"""Progressive disclosure for review and lifecycle actions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import streamlit as st

from application_workspace.models import ApplicationApprovalState
from presentation.labels import discourages_primary_approve
from recommendation_engine import ApprovalStatus
from state_hygiene import is_actionable_queue_entry
from workflow_session import capture_approval_for_workspace

if TYPE_CHECKING:
    from application_workspace.models import ApplicationPackage
    from application_workspace.review_manager import ApplicationReviewManager
    from memory.decision_memory import DecisionMemory
    from recommendation_engine import RecommendationResult
    from review_queue_manager import ReviewQueueManager


def render_recommendation_actions(
    rec: RecommendationResult,
    entry_id: str,
    queue: ReviewQueueManager,
    memory: DecisionMemory,
) -> None:
    """Primary approve CTA; reject and archive live under More actions."""
    status = getattr(rec, "approval_status", None)
    if status == ApprovalStatus.APPROVED:
        st.caption(":green[Approved] — use Application workspace to build a package.")
        return
    if status == ApprovalStatus.REJECTED:
        reason = getattr(rec, "rejection_reason", "") or "No reason recorded"
        st.caption(f":orange[Rejected] — {reason}")
        return
    if status == ApprovalStatus.ARCHIVED:
        st.caption(":gray[Archived]")
        return

    # Defensive, state-safe rendering: never show actions for missing/stale queue rows.
    current_entry: dict | None = None
    if entry_id:
        try:
            current_entry = queue.get_entry(entry_id)
        except KeyError:
            current_entry = None

    if not is_actionable_queue_entry(current_entry):
        # Hide actions completely for stale/orphaned entries; keep a soft hint.
        if entry_id:
            st.warning("This recommendation was refreshed. Please rerun analysis.")
        return

    priority = getattr(rec.recommendation_priority, "value", None) or str(
        rec.recommendation_priority or "",
    )
    limited_fit = discourages_primary_approve(
        eligibility_passed=bool(rec.eligibility_passed),
        recommendation_priority=priority,
    )

    if limited_fit:
        if not rec.eligibility_passed:
            st.caption(
                ":gray[Gated role] — eligibility checks did not pass. "
                "Review gaps below; use **More actions** only if you still want to record a decision.",
            )
        else:
            st.caption(
                ":gray[Limited fit] — moderate alignment. "
                "Prefer stronger matches for packages; use **More actions** to reject or archive.",
            )
    elif st.button(
        "Approve",
        key=f"approve_{rec.job_id}",
        type="primary",
        use_container_width=True,
    ):
        try:
            updated = queue.approve(entry_id)
        except KeyError:
            st.warning("This recommendation was refreshed. Please rerun analysis.")
            st.rerun()
            return
        memory.record_approval(rec)
        _apply_queue_entry_to_rec(rec, updated)
        capture_approval_for_workspace(entry_id=entry_id, job_id=rec.job_id)
        st.success("Approved — open Application workspace to generate your package.")
        st.rerun()

    with st.popover("More actions"):
        st.caption(
            "Record a decision without promoting this role to your application workspace."
            if limited_fit
            else "Optional — reject or archive without approving.",
        )
        if limited_fit and st.button(
            "Approve anyway",
            key=f"approve_override_{rec.job_id}",
            use_container_width=True,
        ):
            try:
                updated = queue.approve(entry_id)
            except KeyError:
                st.warning("This recommendation was refreshed. Please rerun analysis.")
                st.rerun()
                return
            memory.record_approval(rec)
            _apply_queue_entry_to_rec(rec, updated)
            capture_approval_for_workspace(entry_id=entry_id, job_id=rec.job_id)
            st.success("Approved — open Application workspace to generate your package.")
            st.rerun()
        reject_reason = st.text_input(
            "Rejection reason",
            key=f"reject_reason_{rec.job_id}",
            placeholder="e.g. product-heavy mismatch",
        )
        col_reject, col_archive = st.columns(2)
        with col_reject:
            if st.button("Reject", key=f"reject_{rec.job_id}", use_container_width=True):
                try:
                    updated = queue.reject(entry_id, reason=reject_reason)
                except KeyError:
                    st.warning("This recommendation was refreshed. Please rerun analysis.")
                    st.rerun()
                    return
                memory.record_rejection(rec, reason=reject_reason)
                _apply_queue_entry_to_rec(rec, updated)
                rec.rejection_reason = reject_reason
                st.warning("Rejected and saved.")
                st.rerun()
        with col_archive:
            if st.button("Archive", key=f"archive_{rec.job_id}", use_container_width=True):
                try:
                    updated = queue.archive(entry_id)
                except KeyError:
                    st.warning("This recommendation was refreshed. Please rerun analysis.")
                    st.rerun()
                    return
                _apply_queue_entry_to_rec(rec, updated)
                st.info("Archived.")
                st.rerun()


def _apply_queue_entry_to_rec(rec: RecommendationResult, entry: dict) -> None:
    """Keep in-memory card state aligned with persisted queue row."""
    payload = entry.get("recommendation") or {}
    raw_status = payload.get("approval_status")
    if raw_status:
        try:
            rec.approval_status = ApprovalStatus(str(raw_status))
        except ValueError:
            pass
    reason = entry.get("rejection_reason") or payload.get("rejection_reason")
    if reason:
        rec.rejection_reason = str(reason)


def _primary_lifecycle_action(
    allowed: set[ApplicationApprovalState],
) -> ApplicationApprovalState | None:
    """Pick the single most common next step to surface as primary."""
    for candidate in (
        ApplicationApprovalState.APPROVED,
        ApplicationApprovalState.UNDER_REVIEW,
        ApplicationApprovalState.EXPORTED,
        ApplicationApprovalState.REOPENED,
    ):
        if candidate in allowed:
            return candidate
    return next(iter(allowed), None)


def render_lifecycle_actions(
    pkg: ApplicationPackage,
    package_id: str,
    allowed: set[ApplicationApprovalState],
    review_mgr: ApplicationReviewManager,
    export_root,
    *,
    on_transition: Callable,
    on_export_paths: Callable[[dict], None] | None = None,
) -> None:
    """One primary lifecycle button; secondary transitions under More actions."""
    from application_workspace.export import export_package

    primary = _primary_lifecycle_action(allowed)
    secondary = allowed - ({primary} if primary else set())
    notes_key = f"lifecycle_notes_{package_id}"
    reason_key = f"lifecycle_reason_{package_id}"
    if notes_key not in st.session_state:
        st.session_state[notes_key] = pkg.reviewer_notes or ""

    label_map = {
        ApplicationApprovalState.UNDER_REVIEW: "Mark under review",
        ApplicationApprovalState.APPROVED: "Approve package",
        ApplicationApprovalState.REJECTED: "Reject package",
        ApplicationApprovalState.EXPORTED: "Export package",
        ApplicationApprovalState.REOPENED: "Reopen package",
        ApplicationApprovalState.ARCHIVED: "Archive package",
    }

    if primary:
        if st.button(
            label_map.get(primary, primary.value.replace("_", " ").title()),
            type="primary",
            key=f"lifecycle_primary_{package_id}_{primary.value}",
            use_container_width=True,
        ):
            _run_lifecycle_action(
                primary,
                package_id,
                pkg,
                review_mgr,
                export_root,
                notes=st.session_state.get(notes_key, ""),
                reason=st.session_state.get(reason_key, ""),
                on_transition=on_transition,
                on_export_paths=on_export_paths,
            )
            st.rerun()
    elif not allowed:
        st.caption("No lifecycle transitions available for the current state.")

    if secondary:
        with st.popover("More actions"):
            st.text_input(
                "Review notes (optional)",
                key=notes_key,
            )
            st.text_input(
                "Action reason (optional)",
                key=reason_key,
            )
            st.caption(
                f"Other transitions: {', '.join(s.value.replace('_', ' ') for s in sorted(secondary, key=lambda x: x.value))}"
            )
            for state in sorted(secondary, key=lambda x: x.value):
                if st.button(
                    label_map.get(state, state.value.replace("_", " ").title()),
                    key=f"lifecycle_{package_id}_{state.value}",
                    use_container_width=True,
                ):
                    _run_lifecycle_action(
                        state,
                        package_id,
                        pkg,
                        review_mgr,
                        export_root,
                        notes=st.session_state.get(notes_key, ""),
                        reason=st.session_state.get(reason_key, ""),
                        on_transition=on_transition,
                        on_export_paths=on_export_paths,
                    )
                    st.rerun()


def _run_lifecycle_action(
    state: ApplicationApprovalState,
    package_id: str,
    pkg: ApplicationPackage,
    review_mgr: ApplicationReviewManager,
    export_root,
    *,
    notes: str,
    reason: str,
    on_transition: Callable,
    on_export_paths: Callable[[dict], None] | None,
) -> None:
    from application_workspace.export import export_package

    if state == ApplicationApprovalState.UNDER_REVIEW:
        on_transition(review_mgr.mark_under_review(package_id, notes=notes))
    elif state == ApplicationApprovalState.APPROVED:
        on_transition(review_mgr.approve(package_id, notes=notes))
    elif state == ApplicationApprovalState.REJECTED:
        on_transition(review_mgr.reject(package_id, reason=reason, notes=notes))
    elif state == ApplicationApprovalState.EXPORTED:
        paths = export_package(pkg, export_root)
        on_transition(review_mgr.mark_exported(package_id, notes=notes))
        if on_export_paths:
            on_export_paths(paths)
    elif state == ApplicationApprovalState.REOPENED:
        on_transition(review_mgr.reopen(package_id, notes=notes))
    elif state == ApplicationApprovalState.ARCHIVED:
        on_transition(review_mgr.archive(package_id, notes=notes))
