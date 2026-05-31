"""Naukri-style job export parser (paste / JSON export, no scraping)."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from job_sources.generic_job_parser import GenericJobParser
from job_sources.job_posting import JobPosting


class NaukriJobParser:
    """Parse Naukri pasted listings or JSON job dumps."""

    SOURCE = "naukri"

    def __init__(self) -> None:
        self._generic = GenericJobParser()

    def parse_pasted(self, text: str, *, job_id: str | None = None) -> JobPosting:
        meta = self._extract_naukri_metadata(text)
        return self._generic._build_posting(
            job_id=job_id or str(uuid.uuid4()),
            title=meta.get("title", ""),
            company=meta.get("company", ""),
            location=meta.get("location", ""),
            raw_text=text.strip(),
            source=self.SOURCE,
        )

    def parse_json_file(self, path: str | Path) -> list[JobPosting]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else payload.get("jobs", [payload])
        results: list[JobPosting] = []
        for item in items:
            raw = item.get("jobDescription") or item.get("description") or item.get("raw_text", "")
            results.append(
                self._generic._build_posting(
                    job_id=str(item.get("job_id") or item.get("jobId") or uuid.uuid4()),
                    title=str(item.get("title") or item.get("designation", "")),
                    company=str(item.get("company") or item.get("companyName", "")),
                    location=str(item.get("location") or item.get("jobLocation", "")),
                    raw_text=str(raw).strip(),
                    source=self.SOURCE,
                )
            )
        return results

    def _extract_naukri_metadata(self, text: str) -> dict[str, str]:
        title = ""
        company = ""
        location = ""
        m_title = re.search(r"(?:Job Title|Designation)\s*[:\-]\s*(.+)", text, re.I)
        if m_title:
            title = m_title.group(1).strip()
        m_company = re.search(r"(?:Company|Employer)\s*[:\-]\s*(.+)", text, re.I)
        if m_company:
            company = m_company.group(1).strip()
        m_loc = re.search(r"(?:Location|Job Location)\s*[:\-]\s*(.+)", text, re.I)
        if m_loc:
            location = m_loc.group(1).strip()
        if not title:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if lines:
                title = lines[0]
        return {"title": title, "company": company, "location": location}
