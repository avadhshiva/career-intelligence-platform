"""Deterministic application package lifecycle state machine."""

from __future__ import annotations

from dataclasses import dataclass

from application_workspace.models import ApplicationApprovalState


@dataclass
class TransitionResult:
    """Outcome of a lifecycle transition attempt."""

    success: bool
    package_id: str
    from_state: ApplicationApprovalState
    to_state: ApplicationApprovalState
    message: str = ""
    warning: str = ""

    @property
    def user_message(self) -> str:
        if self.success:
            return self.message or f"Moved to {self.to_state.value}."
        return self.warning or self.message


_ALLOWED_TRANSITIONS: dict[ApplicationApprovalState, set[ApplicationApprovalState]] = {
    ApplicationApprovalState.GENERATED: {
        ApplicationApprovalState.UNDER_REVIEW,
        ApplicationApprovalState.APPROVED,
        ApplicationApprovalState.REJECTED,
    },
    ApplicationApprovalState.UNDER_REVIEW: {
        ApplicationApprovalState.APPROVED,
        ApplicationApprovalState.REJECTED,
    },
    ApplicationApprovalState.APPROVED: {
        ApplicationApprovalState.EXPORTED,
        ApplicationApprovalState.ARCHIVED,
    },
    ApplicationApprovalState.EXPORTED: {
        ApplicationApprovalState.ARCHIVED,
        ApplicationApprovalState.REOPENED,
    },
    ApplicationApprovalState.REOPENED: {
        ApplicationApprovalState.UNDER_REVIEW,
        ApplicationApprovalState.APPROVED,
    },
    ApplicationApprovalState.REJECTED: {
        ApplicationApprovalState.ARCHIVED,
    },
    ApplicationApprovalState.ARCHIVED: set(),
}


def allowed_targets(state: ApplicationApprovalState) -> set[ApplicationApprovalState]:
    return set(_ALLOWED_TRANSITIONS.get(state, set()))


def can_transition(
    from_state: ApplicationApprovalState,
    to_state: ApplicationApprovalState,
) -> bool:
    if from_state == to_state:
        return True
    return to_state in _ALLOWED_TRANSITIONS.get(from_state, set())


def transition_warning(
    from_state: ApplicationApprovalState,
    to_state: ApplicationApprovalState,
) -> str:
    allowed = sorted(s.value for s in allowed_targets(from_state))
    if allowed:
        allowed_text = ", ".join(allowed)
    else:
        allowed_text = "none (terminal state)"
    return (
        f"Cannot move from '{from_state.value}' to '{to_state.value}'. "
        f"Allowed next states: {allowed_text}."
    )
