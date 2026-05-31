"""Job discovery agent — discovers and normalizes job postings for matching.

Phase 5 placeholder: no browser automation or auto-apply. Uses embedded
deterministic intelligence engine for parsing and capability extraction only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from career_intelligence_engine.intelligence.job_capability_vector import extract_job_vector
from career_intelligence_engine.intelligence.job_parser import JobDescriptionParser
from career_intelligence_engine.models.job_profile import JobProfile


@dataclass
class DiscoveredJob:
    """Normalized job record ready for JD matching."""

    job_id: str
    title: str
    company: str
    raw_text: str
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)


class JobDiscoveryAgent:
    """Collects job descriptions and builds capability vectors via the frozen engine."""

    def __init__(self) -> None:
        self._parser = JobDescriptionParser()

    def ingest_text(self, job_id: str, title: str, company: str, jd_text: str) -> DiscoveredJob:
        """Parse JD text and attach structured parse output (no external APIs)."""
        job_profile: JobProfile = self._parser.parse(jd_text)
        vector = extract_job_vector(
            corpus=jd_text,
            title=job_profile.title or title,
            job_hints={
                "primary_role_family": job_profile.primary_role_family,
            },
        )
        return DiscoveredJob(
            job_id=job_id,
            title=title,
            company=company,
            raw_text=jd_text,
            metadata={
                "job_profile": job_profile,
                "capability_vector": vector,
            },
        )
