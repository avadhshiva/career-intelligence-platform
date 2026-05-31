"""Deterministic resume text extraction and structural parsing."""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime
from pathlib import Path

from career_intelligence_engine.models.ontology import ParsedResume

logger = logging.getLogger(__name__)

_SECTION_HEADERS = re.compile(
    r"^(?P<header>(?:experience|work experience|professional experience|"
    r"employment|education|skills|technical skills|summary|profile|"
    r"certifications|projects|leadership))\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}(?:[-.\s]?\d{1,4})?"
)
_DATE_RANGE = re.compile(
    r"(?P<start>(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}"
    r"|\d{1,2}/\d{4}|\d{4})\s*[-–—to]+\s*"
    r"(?P<end>present|current|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}"
    r"|\d{1,2}/\d{4}|\d{4})",
    re.IGNORECASE,
)
_YEAR_ONLY = re.compile(r"\b(19|20)\d{2}\b")
_LOCATION_HINT = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*(?:[A-Z]{2}|[A-Z][a-z]+))\b"
)
_TITLE_LINE = re.compile(
    r"^[\|\-•\s]*(?P<title>[A-Za-z][^\n|]{4,80}?)"
    r"(?:\s+[\|\-]\s+|\s+at\s+|\s+@\s+)(?P<company>[A-Za-z][^\n|]{2,60})",
    re.IGNORECASE | re.MULTILINE,
)
_BULLET = re.compile(r"^[\s]*(?:[•\-\*▪]|\d+\.)\s+(.+)$", re.MULTILINE)

_MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


class ResumeParser:
    """Extract structured fields from resume files without LLM calls."""

    SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}

    def parse_bytes(self, content: bytes, filename: str) -> ParsedResume:
        suffix = Path(filename).suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{suffix}'. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )
        raw = self._extract_text(content, suffix)
        return self.parse_text(raw)

    def parse_text(self, raw_text: str) -> ParsedResume:
        text = self._normalize(raw_text)
        sections = self._split_sections(text)
        emails = list(dict.fromkeys(_EMAIL.findall(text)))
        phones = list(dict.fromkeys(_PHONE.findall(text)))
        locations = list(dict.fromkeys(_LOCATION_HINT.findall(text)))
        date_ranges = [m.group(0) for m in _DATE_RANGE.finditer(text)]
        job_titles, employers = self._extract_roles(text, sections)
        bullets = [m.group(1).strip() for m in _BULLET.finditer(text)]
        years = self._estimate_years(date_ranges, text)
        name = self._infer_name(text, emails)

        parsed = ParsedResume(
            raw_text=text,
            full_name=name,
            emails=emails,
            phones=phones,
            locations=locations,
            job_titles=job_titles,
            employers=employers,
            date_ranges=date_ranges,
            years_experience=years,
            sections=sections,
            bullets=bullets,
        )
        logger.info(
            "Parsed resume: titles=%d bullets=%d years=%s",
            len(job_titles),
            len(bullets),
            years,
        )
        return parsed

    def _extract_text(self, content: bytes, suffix: str) -> str:
        if suffix == ".txt":
            return content.decode("utf-8", errors="replace")
        if suffix == ".pdf":
            return self._pdf_to_text(content)
        if suffix == ".docx":
            return self._docx_to_text(content)
        return ""

    def _pdf_to_text(self, content: bytes) -> str:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)

    def _docx_to_text(self, content: bytes) -> str:
        from docx import Document

        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _normalize(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_sections(self, text: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        matches = list(_SECTION_HEADERS.finditer(text))
        if not matches:
            sections["body"] = text
            return sections
        for idx, match in enumerate(matches):
            header = match.group("header").lower().replace(" ", "_")
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            sections[header] = text[start:end].strip()
        return sections

    def _extract_roles(
        self, text: str, sections: dict[str, str]
    ) -> tuple[list[str], list[str]]:
        titles: list[str] = []
        employers: list[str] = []
        exp_text = " ".join(
            sections.get(k, "")
            for k in ("experience", "work_experience", "professional_experience", "employment")
        )
        search_text = exp_text or text
        for match in _TITLE_LINE.finditer(search_text):
            title = match.group("title").strip()
            company = match.group("company").strip()
            if title and title not in titles:
                titles.append(title)
            if company and company not in employers:
                employers.append(company)
        # Fallback: first few non-header lines in experience often are titles
        if not titles and exp_text:
            for line in exp_text.split("\n")[:12]:
                line = line.strip()
                if 4 < len(line) < 90 and not _DATE_RANGE.search(line):
                    titles.append(line)
                    if len(titles) >= 5:
                        break
        return titles, employers

    def _estimate_years(self, date_ranges: list[str], text: str) -> float | None:
        spans: list[tuple[datetime, datetime]] = []
        now = datetime.now()
        for dr in date_ranges:
            m = _DATE_RANGE.search(dr)
            if not m:
                continue
            start = self._parse_date_token(m.group("start"))
            end_raw = m.group("end").lower()
            end = now if end_raw in ("present", "current") else self._parse_date_token(end_raw)
            if start and end and end >= start:
                spans.append((start, end))
        if spans:
            earliest = min(s[0] for s in spans)
            latest = max(s[1] for s in spans)
            return round((latest - earliest).days / 365.25, 1)
        years = [int(y) for y in _YEAR_ONLY.findall(text)]
        if len(years) >= 2:
            return float(max(years) - min(years))
        return None

    def _parse_date_token(self, token: str) -> datetime | None:
        token = token.strip().lower()
        if re.fullmatch(r"\d{4}", token):
            return datetime(int(token), 1, 1)
        m = re.match(r"([a-z]{3,9})\.?\s+(\d{4})", token)
        if m:
            month_key = m.group(1)[:3]
            month = _MONTH_MAP.get(month_key)
            if month:
                return datetime(int(m.group(2)), month, 1)
        m = re.match(r"(\d{1,2})/(\d{4})", token)
        if m:
            return datetime(int(m.group(2)), int(m.group(1)), 1)
        return None

    def _infer_name(self, text: str, emails: list[str]) -> str | None:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if not lines:
            return None
        first = lines[0]
        if len(first) > 60 or "@" in first or _PHONE.search(first):
            if emails:
                local = emails[0].split("@")[0]
                parts = re.split(r"[._]", local)
                return " ".join(p.capitalize() for p in parts if p.isalpha())
            return None
        if re.match(r"^[A-Za-z][A-Za-z\s\.\-']{2,50}$", first):
            return first
        return None
