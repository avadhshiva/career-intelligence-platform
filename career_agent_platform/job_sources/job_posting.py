"""Unified job posting schema for Phase 5A ingestion."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from career_intelligence_engine.models.job_profile import JobProfile


@dataclass
class JobPosting:
    """Normalized job record after source-specific parsing."""

    job_id: str
    source: str
    company: str
    title: str
    location: str
    raw_text: str
    parsed_job_profile: JobProfile | None = None
    parsed_capability_vector: dict[str, float] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.parsed_job_profile is not None:
            data["parsed_job_profile"] = self.parsed_job_profile.model_dump(mode="json")
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobPosting:
        profile = None
        raw_profile = data.get("parsed_job_profile")
        if raw_profile:
            profile = JobProfile.model_validate(raw_profile)
        return cls(
            job_id=str(data["job_id"]),
            source=str(data.get("source", "generic")),
            company=str(data.get("company", "")),
            title=str(data.get("title", "")),
            location=str(data.get("location", "")),
            raw_text=str(data.get("raw_text", "")),
            parsed_job_profile=profile,
            parsed_capability_vector=dict(data.get("parsed_capability_vector") or {}),
            created_at=str(data.get("created_at", datetime.now(timezone.utc).isoformat())),
        )
