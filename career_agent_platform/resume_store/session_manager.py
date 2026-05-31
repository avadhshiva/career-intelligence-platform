"""Session helpers for active resume identity (Streamlit + testable dict fallback)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from resume_store.models import CanonicalResume, ResumeIdentity
from monitoring.ops_log import log_event
from resume_store.storage import (
    CanonicalResumeStore,
    ResumeStore,
    compute_resume_id,
    load_active_resume_id,
    save_active_resume_id,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dominant_dimensions(profile: CandidateProfile) -> list[str]:
    vec = profile.capability_vector or {}
    # deterministic: pick highest-weight dimensions from vector
    ranked = sorted(((k, float(v)) for k, v in vec.items()), key=lambda kv: (-kv[1], kv[0]))
    return [k for k, v in ranked if v >= 0.45][:6]


def _resume_label(profile: CandidateProfile) -> str:
    family = profile.primary_career_track
    display = ROLE_FAMILIES[family].display_name if family in ROLE_FAMILIES else family.value.replace("_", " ").title()
    ai = (profile.ai_maturity.value if profile.ai_maturity else "none").replace("_", " ").title()
    yrs = profile.years_experience
    yrs_label = f"{int(round(yrs))}y" if isinstance(yrs, (int, float)) and yrs > 0 else ""
    parts = [p for p in [display, yrs_label, ai] if p]
    return " — ".join(parts) if parts else display or "Resume"


def build_resume_identity(
    *,
    filename: str,
    raw_text: str,
    profile: CandidateProfile,
    uploaded_at: str | None = None,
) -> ResumeIdentity:
    resume_id = compute_resume_id(raw_text=raw_text)
    primary = profile.primary_career_track.value
    adjacent = [a.value for a in (profile.adjacent_role_families or [])][:5]
    top_skills = list(profile.top_skills or [])[:12]
    yrs = float(profile.years_experience) if profile.years_experience is not None else None
    summary = (
        f"Primary track: {ROLE_FAMILIES[profile.primary_career_track].display_name}. "
        f"Top skills: {', '.join(top_skills[:6]) or '—'}."
    )
    return ResumeIdentity(
        resume_id=resume_id,
        filename=filename or "uploaded_resume",
        uploaded_at=uploaded_at or _utc_now_iso(),
        raw_text=(raw_text or "").strip(),
        parsed_profile_summary=summary,
        primary_role_family=primary,
        adjacent_roles=adjacent,
        years_experience=yrs,
        dominant_dimensions=_dominant_dimensions(profile),
        top_skills=top_skills,
        ai_maturity=(profile.ai_maturity.value if profile.ai_maturity else "none"),
        transformation_focus=float(profile.transformation_focus or 0.0),
        recommended_resume_label=_resume_label(profile),
    )


def build_canonical_resume(
    *,
    file_name: str,
    resume_text: str,
    profile: CandidateProfile,
    created_at: str | None = None,
    normalized_profile: dict[str, Any] | None = None,
    routing_metadata: dict[str, Any] | None = None,
) -> CanonicalResume:
    resume_id = compute_resume_id(raw_text=resume_text)
    top_skills = list(profile.top_skills or [])[:24]
    yrs = float(profile.years_experience) if profile.years_experience is not None else None
    role_family = profile.primary_career_track.value

    parsed_payload = profile.model_dump(mode="json")
    normalized_payload = normalized_profile or {
        "primary_career_track": role_family,
        "years_experience": yrs,
        "top_skills": top_skills,
        "ai_maturity": (profile.ai_maturity.value if profile.ai_maturity else "none"),
        "transformation_focus": float(profile.transformation_focus or 0.0),
        "capability_vector": dict(profile.capability_vector or {}),
        "role_family_scores": dict(profile.role_family_scores or {}),
    }

    return CanonicalResume(
        resume_id=resume_id,
        file_name=file_name or "uploaded_resume",
        created_at=created_at or _utc_now_iso(),
        resume_text=(resume_text or "").strip(),
        parsed_profile=dict(parsed_payload or {}),
        normalized_profile=dict(normalized_payload or {}),
        resume_identity={
            "role_family": role_family,
            "experience_years": yrs,
            "top_skills": top_skills,
            "recommended_resume_label": _resume_label(profile),
            "dominant_dimensions": _dominant_dimensions(profile),
            "parsed_profile_summary": (
                f"Primary track: {ROLE_FAMILIES[profile.primary_career_track].display_name}. "
                f"Top skills: {', '.join(top_skills[:6]) or '—'}."
            ),
        },
        routing_metadata=dict(routing_metadata or {}),
    )


def set_active_resume_id(session_state: MutableMapping[str, Any], resume_id: str) -> None:
    session_state["active_resume_id"] = resume_id
    save_active_resume_id(resume_id)


def get_active_resume_id(session_state: Mapping[str, Any]) -> str:
    return str(session_state.get("active_resume_id") or "").strip()


@dataclass(frozen=True)
class ActiveResumeResult:
    resume: CanonicalResume | None
    resume_id: str


def get_active_resume(
    session_state: MutableMapping[str, Any],
    *,
    store: CanonicalResumeStore | None = None,
) -> ActiveResumeResult:
    # Session state is cache only — disk marker is the restart-safe source.
    if "active_resume_id" not in session_state:
        session_state["active_resume_id"] = load_active_resume_id()
    rid = get_active_resume_id(session_state)
    store = store or CanonicalResumeStore()
    return ActiveResumeResult(resume=store.load(rid), resume_id=rid)


def persist_and_activate_resume(
    *,
    session_state: MutableMapping[str, Any],
    store: ResumeStore,
    identity: ResumeIdentity,
) -> None:
    store.save(identity)
    set_active_resume_id(session_state, identity.resume_id)


def persist_and_activate_canonical_resume(
    *,
    session_state: MutableMapping[str, Any],
    store: CanonicalResumeStore,
    resume: CanonicalResume,
) -> None:
    from demo_mode import persistence_writes_enabled

    if not persistence_writes_enabled():
        set_active_resume_id(session_state, resume.resume_id)
        log_event(
            "canonical_resume_persist_skipped",
            resume_id=resume.resume_id,
            reason="demo_mode",
        )
        return
    try:
        store.save(resume)
        set_active_resume_id(session_state, resume.resume_id)
        has_profile = bool(resume.parsed_profile)
        log_event(
            "canonical_resume_persisted",
            resume_id=resume.resume_id,
            file_name=resume.file_name,
            has_parsed_profile=has_profile,
        )
    except Exception as exc:
        log_event(
            "canonical_resume_persist_failed",
            level=logging.ERROR,
            resume_id=resume.resume_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

