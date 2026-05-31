"""Persistent resume identity objects (deterministic, recruiter-readable)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CanonicalResume:
    """
    The single persisted source of truth for resume payload + derived identity.

    This is intentionally redundant with UI fields so pages never have to stitch
    together session fragments after restart.
    """

    resume_id: str
    file_name: str
    created_at: str = field(default_factory=_utc_now_iso)

    resume_text: str = ""

    parsed_profile: dict[str, Any] = field(default_factory=dict)
    normalized_profile: dict[str, Any] = field(default_factory=dict)

    resume_identity: dict[str, Any] = field(default_factory=dict)
    routing_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalResume":
        d = data or {}
        # Back-compat: v0 persisted ResumeIdentity objects stored at this path.
        resume_text = str(d.get("resume_text") or d.get("raw_text") or "").strip()

        identity_block = d.get("resume_identity")
        if not isinstance(identity_block, dict):
            role_family = str(d.get("role_family") or d.get("primary_role_family") or "").strip()
            exp = d.get("experience_years")
            if exp is None:
                exp = d.get("years_experience")
            identity_block = {
                "role_family": role_family,
                "experience_years": exp,
                "top_skills": d.get("top_skills") or [],
            }

        top = identity_block.get("top_skills") or []
        if isinstance(top, str):
            top = [s.strip() for s in top.split(",") if s.strip()]

        exp = identity_block.get("experience_years")
        try:
            exp_val = float(exp) if exp is not None and exp != "" else None
        except Exception:
            exp_val = None

        identity_block["experience_years"] = exp_val
        identity_block["top_skills"] = list(top)[:24]
        return cls(
            resume_id=str(d.get("resume_id") or "").strip(),
            file_name=str(d.get("file_name") or d.get("filename") or "").strip() or "uploaded_resume",
            created_at=str(d.get("created_at") or d.get("uploaded_at") or _utc_now_iso()),
            resume_text=resume_text,
            parsed_profile=dict(d.get("parsed_profile") or {}),
            normalized_profile=dict(d.get("normalized_profile") or {}),
            resume_identity=dict(identity_block),
            routing_metadata=dict(d.get("routing_metadata") or {}),
        )


@dataclass(frozen=True)
class ResumeIdentity:
    resume_id: str
    filename: str
    uploaded_at: str
    raw_text: str
    parsed_profile_summary: str
    primary_role_family: str
    adjacent_roles: list[str] = field(default_factory=list)
    years_experience: float | None = None
    dominant_dimensions: list[str] = field(default_factory=list)
    top_skills: list[str] = field(default_factory=list)
    ai_maturity: str = "none"
    transformation_focus: float = 0.0
    recommended_resume_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResumeIdentity":
        return cls(
            resume_id=str(data.get("resume_id") or ""),
            filename=str(data.get("filename") or ""),
            uploaded_at=str(data.get("uploaded_at") or _utc_now_iso()),
            raw_text=str(data.get("raw_text") or ""),
            parsed_profile_summary=str(data.get("parsed_profile_summary") or ""),
            primary_role_family=str(data.get("primary_role_family") or ""),
            adjacent_roles=list(data.get("adjacent_roles") or []),
            years_experience=(
                float(data["years_experience"]) if data.get("years_experience") is not None else None
            ),
            dominant_dimensions=list(data.get("dominant_dimensions") or []),
            top_skills=list(data.get("top_skills") or []),
            ai_maturity=str(data.get("ai_maturity") or "none"),
            transformation_focus=float(data.get("transformation_focus") or 0.0),
            recommended_resume_label=str(data.get("recommended_resume_label") or ""),
        )

