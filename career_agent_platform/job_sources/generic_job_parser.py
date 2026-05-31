"""Generic job ingestion — pasted text, JSON files, exports, mock feeds."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from career_intelligence_engine.intelligence.job_capability_vector import extract_job_vector
from career_intelligence_engine.intelligence.job_parser import JobDescriptionParser

from job_sources.job_posting import JobPosting


class GenericJobParser:
    """Parse jobs from common non-scraped sources."""

    SOURCE = "generic"

    def __init__(self) -> None:
        self._parser = JobDescriptionParser()

    def parse_pasted_text(
        self,
        text: str,
        *,
        job_id: str | None = None,
        title: str = "",
        company: str = "",
        location: str = "",
    ) -> JobPosting:
        return self._build_posting(
            job_id=job_id or str(uuid.uuid4()),
            title=title,
            company=company,
            location=location,
            raw_text=text.strip(),
            source=self.SOURCE,
        )

    def parse_json_file(self, path: str | Path) -> list[JobPosting]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "jobs" in payload:
            items = payload["jobs"]
        elif isinstance(payload, list):
            items = payload
        else:
            items = [payload]
        return [self.parse_json_record(item) for item in items]

    def parse_json_record(self, record: dict[str, Any]) -> JobPosting:
        raw = record.get("raw_text") or record.get("jd_text") or record.get("description") or ""
        if not raw and record.get("body"):
            raw = str(record["body"])
        return self._build_posting(
            job_id=str(record.get("job_id") or uuid.uuid4()),
            title=str(record.get("title", "")),
            company=str(record.get("company", "")),
            location=str(record.get("location", "")),
            raw_text=str(raw).strip(),
            source=str(record.get("source", self.SOURCE)),
        )

    def parse_text_file(self, path: str | Path) -> JobPosting:
        text = Path(path).read_text(encoding="utf-8")
        stem = Path(path).stem
        return self.parse_pasted_text(text, job_id=stem, title=stem.replace("_", " ").title())

    def parse_mock_feed(self, feed: list[dict[str, Any]]) -> list[JobPosting]:
        return [self.parse_json_record(item) for item in feed]

    def _build_posting(
        self,
        *,
        job_id: str,
        title: str,
        company: str,
        location: str,
        raw_text: str,
        source: str,
    ) -> JobPosting:
        profile = self._parser.parse(raw_text)
        resolved_title = title or profile.title or "Untitled Role"
        resolved_company = company or "Unknown"
        vector = extract_job_vector(
            corpus=raw_text,
            title=resolved_title,
            job_hints={"primary_role_family": profile.primary_role_family},
        )
        return JobPosting(
            job_id=job_id,
            source=source,
            company=resolved_company,
            title=resolved_title,
            location=location,
            raw_text=raw_text,
            parsed_job_profile=profile,
            parsed_capability_vector=vector,
        )
