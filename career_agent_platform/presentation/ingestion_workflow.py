"""Recommendations engine-room — pipeline storytelling and workflow state (UI-only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import streamlit as st

from demo_mode import is_demo_mode
from resume_store.storage import CanonicalResumeStore
from workflow_session import get_match_postings, get_parsed_resume


class WorkflowPhase(str, Enum):
    NO_RESUME = "no_resume"
    RESUME_READY = "resume_ready"
    ANALYSIS_COMPLETE = "analysis_complete"
    APPROVALS_STARTED = "approvals_started"


@dataclass(frozen=True)
class WorkflowSnapshot:
    phase: WorkflowPhase
    has_resume: bool
    has_profile: bool
    jd_count: int
    match_count: int
    approved_count: int
    resume_label: str


_PIPELINE_STAGES: tuple[tuple[str, str], ...] = (
    ("input", "Resume & JDs"),
    ("analysis", "Analysis"),
    ("ranked", "Ranked matches"),
    ("approval", "Approval"),
    ("workspace", "Application package"),
)


def _resume_label() -> str:
    rid = str(st.session_state.get("active_resume_id") or "").strip()
    if rid:
        canonical = CanonicalResumeStore().load(rid)
        if canonical and canonical.file_name:
            return str(canonical.file_name)
    return "Resume on file" if get_parsed_resume() else ""


def build_workflow_snapshot(
    *,
    recommendations: list,
    approved_count: int,
) -> WorkflowSnapshot:
    has_profile = st.session_state.get("career_profile") is not None
    rid = str(st.session_state.get("active_resume_id") or "").strip()
    has_canonical = bool(rid and CanonicalResumeStore().load(rid))
    has_parsed = bool(get_parsed_resume())
    has_resume = has_canonical or has_parsed or has_profile
    jd_count = len(get_match_postings())
    match_count = len(recommendations or [])

    if match_count > 0 and approved_count >= 1:
        phase = WorkflowPhase.APPROVALS_STARTED
    elif match_count > 0:
        phase = WorkflowPhase.ANALYSIS_COMPLETE
    elif has_resume:
        phase = WorkflowPhase.RESUME_READY
    else:
        phase = WorkflowPhase.NO_RESUME

    label = _resume_label() if has_resume else ""
    return WorkflowSnapshot(
        phase=phase,
        has_resume=has_resume,
        has_profile=has_profile,
        jd_count=jd_count,
        match_count=match_count,
        approved_count=approved_count,
        resume_label=label,
    )


def _stage_status(stage_id: str, snap: WorkflowSnapshot) -> str:
    """Return CSS class: done | active | todo."""
    phase = snap.phase
    if stage_id == "input":
        if phase == WorkflowPhase.NO_RESUME:
            return "active"
        return "done"
    if stage_id == "analysis":
        if phase == WorkflowPhase.NO_RESUME:
            return "todo"
        if phase == WorkflowPhase.RESUME_READY:
            return "active"
        return "done"
    if stage_id == "ranked":
        if phase in (WorkflowPhase.NO_RESUME, WorkflowPhase.RESUME_READY):
            return "todo"
        if phase == WorkflowPhase.ANALYSIS_COMPLETE and snap.approved_count == 0:
            return "active"
        return "done" if snap.match_count > 0 else "todo"
    if stage_id == "approval":
        if snap.match_count == 0:
            return "todo"
        if snap.approved_count > 0:
            return "done"
        return "active"
    if stage_id == "workspace":
        if snap.approved_count > 0:
            return "active"
        return "todo"
    return "todo"


def render_pipeline_rail(snap: WorkflowSnapshot) -> None:
    """Horizontal lifecycle: Input → Analysis → Ranked → Approval → Application."""
    parts: list[str] = []
    for stage_id, label in _PIPELINE_STAGES:
        status = _stage_status(stage_id, snap)
        parts.append(
            f'<span class="ji-pipe-stage ji-pipe-{status}">{label}</span>'
        )
    arrow = '<span class="ji-pipe-arrow" aria-hidden="true">→</span>'
    body = arrow.join(parts)
    st.markdown(
        f'<nav class="ji-pipeline-rail" aria-label="Matching lifecycle">{body}</nav>',
        unsafe_allow_html=True,
    )


def render_workflow_status_line(snap: WorkflowSnapshot) -> None:
    """One-line state summary under the pipeline."""
    if snap.phase == WorkflowPhase.NO_RESUME:
        st.caption("Step 1: upload or paste your resume, add job descriptions, then generate ranked matches.")
        return
    if snap.phase == WorkflowPhase.RESUME_READY:
        jd_note = f"{snap.jd_count} JD(s) saved" if snap.jd_count else "add at least one JD or the sample feed"
        resume_note = snap.resume_label or "Resume ready"
        st.caption(f"{resume_note} · {jd_note} · click **Generate ranked recommendations** to run deterministic matching.")
        return
    if snap.phase == WorkflowPhase.ANALYSIS_COMPLETE:
        st.caption(
            f"{snap.match_count} ranked role(s) · review positioning briefs and approve strong fits · "
            "inputs stay editable below to re-run matching."
        )
        return
    st.caption(
        f"{snap.approved_count} approved · build packages in Application workspace · "
        "you can still replace resume/JDs and re-run scoring below."
    )


def render_engine_room_header(*, snap: WorkflowSnapshot) -> None:
    """Section title for the ingestion panel."""
    if snap.match_count > 0:
        st.subheader("Match inputs — engine room")
        st.caption(
            "Structured ingestion drives deterministic ranking. Change resume or job descriptions, "
            "then regenerate — governance metadata updates on each run."
        )
    else:
        st.subheader("Match inputs")
        if is_demo_mode():
            st.caption(
                "Demo mode: uploads and generation work for this session; nothing is written to disk."
            )
