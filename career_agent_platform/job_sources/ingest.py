"""Route job ingestion by source type."""

from __future__ import annotations

from pathlib import Path

from job_sources.generic_job_parser import GenericJobParser
from job_sources.job_posting import JobPosting
from job_sources.linkedin_parser import LinkedInJobParser
from job_sources.naukri_parser import NaukriJobParser


def ingest_pasted(source: str, text: str, **kwargs) -> JobPosting:
    source_lower = source.lower()
    if source_lower == "linkedin":
        return LinkedInJobParser().parse_pasted(text, job_id=kwargs.get("job_id"))
    if source_lower == "naukri":
        return NaukriJobParser().parse_pasted(text, job_id=kwargs.get("job_id"))
    return GenericJobParser().parse_pasted_text(
        text,
        job_id=kwargs.get("job_id"),
        title=kwargs.get("title", ""),
        company=kwargs.get("company", ""),
        location=kwargs.get("location", ""),
    )


def ingest_file(path: str | Path, source: str = "generic") -> list[JobPosting]:
    path = Path(path)
    source_lower = source.lower()
    if path.suffix.lower() == ".json":
        if source_lower == "linkedin":
            return LinkedInJobParser().parse_json_file(path)
        if source_lower == "naukri":
            return NaukriJobParser().parse_json_file(path)
        return GenericJobParser().parse_json_file(path)
    if source_lower == "linkedin":
        return [LinkedInJobParser().parse_pasted(path.read_text(encoding="utf-8"))]
    if source_lower == "naukri":
        return [NaukriJobParser().parse_pasted(path.read_text(encoding="utf-8"))]
    return [GenericJobParser().parse_text_file(path)]
