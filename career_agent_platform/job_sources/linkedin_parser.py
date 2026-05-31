"""LinkedIn-style job export parser (paste / JSON export, no scraping)."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from job_sources.generic_job_parser import GenericJobParser
from job_sources.job_posting import JobPosting


class LinkedInJobParser:
    """Parse LinkedIn pasted JD blocks or lightweight JSON exports."""

    SOURCE = "linkedin"

    def __init__(self) -> None:
        self._generic = GenericJobParser()

    def parse_pasted(self, text: str, *, job_id: str | None = None) -> JobPosting:
        meta = self._extract_linkedin_metadata(text)
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
            raw = item.get("description") or item.get("jobDescription") or item.get("raw_text", "")
            results.append(
                self._generic._build_posting(
                    job_id=str(item.get("job_id") or item.get("id") or uuid.uuid4()),
                    title=str(item.get("title") or item.get("jobTitle", "")),
                    company=str(item.get("company") or item.get("companyName", "")),
                    location=str(item.get("location") or item.get("jobLocation", "")),
                    raw_text=str(raw).strip(),
                    source=self.SOURCE,
                )
            )
        return results

    def _extract_linkedin_metadata(self, text: str) -> dict[str, str]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        title = ""
        company = ""
        location = ""
        if lines:
            title = lines[0]
        for line in lines[:8]:
            if re.search(r"\b(inc|llc|corp|ltd|technologies|enterprise)\b", line, re.I):
                if not company:
                    company = line
            if re.search(r"\b(remote|hybrid|on-?site)\b", line, re.I) or "," in line:
                if not location and len(line) < 80:
                    location = line
        return {"title": title, "company": company, "location": location}
