"""Canonical company registry — aliases, domains, and employer typing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

ENTERPRISE_FALLBACK_NAME = "Enterprise Technology Organization"

_NOISY_COMPANY_RE = re.compile(r"^tmp[a-z0-9]{4,}$", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"^(unknown|company|n/a|na|null|none)$", re.I)


@dataclass(frozen=True)
class CompanyRecord:
    canonical_name: str
    aliases: tuple[str, ...]
    email_domains: tuple[str, ...] = ()
    company_type: str = "Global Enterprise"


# Deterministic registry — extend here for market intelligence reuse.
COMPANY_REGISTRY: dict[str, CompanyRecord] = {
    "walmart global tech": CompanyRecord(
        canonical_name="Walmart Global Tech",
        aliases=("walmart", "walmart gcc", "walmart global technology", "walmart labs"),
        email_domains=("walmart.com", "wal-mart.com"),
        company_type="Retail Tech",
    ),
    "lowe's": CompanyRecord(
        canonical_name="Lowe's",
        aliases=("lowes", "lowe's india", "lowes india"),
        email_domains=("lowes.com",),
        company_type="Retail Tech",
    ),
    "tesco": CompanyRecord(
        canonical_name="Tesco",
        aliases=("tesco plc",),
        email_domains=("tesco.com",),
        company_type="Retail Tech",
    ),
    "target": CompanyRecord(
        canonical_name="Target",
        aliases=("target corporation",),
        email_domains=("target.com",),
        company_type="Retail Tech",
    ),
    "jp morgan": CompanyRecord(
        canonical_name="JP Morgan Chase",
        aliases=("jpmorgan", "jpmc", "jp morgan chase", "j.p. morgan"),
        email_domains=("jpmorgan.com", "jpmchase.com"),
        company_type="Banking",
    ),
    "lseg": CompanyRecord(
        canonical_name="LSEG",
        aliases=("london stock exchange", "london stock exchange group"),
        email_domains=("lseg.com",),
        company_type="FinTech",
    ),
    "servicenow": CompanyRecord(
        canonical_name="ServiceNow",
        aliases=("service now",),
        email_domains=("servicenow.com",),
        company_type="Enterprise SaaS",
    ),
    "sap": CompanyRecord(
        canonical_name="SAP",
        aliases=("sap se", "sap labs"),
        email_domains=("sap.com",),
        company_type="Enterprise SaaS",
    ),
    "microsoft": CompanyRecord(
        canonical_name="Microsoft",
        aliases=("msft",),
        email_domains=("microsoft.com",),
        company_type="Cloud Platforms",
    ),
    "deloitte": CompanyRecord(
        canonical_name="Deloitte",
        aliases=("deloitte consulting",),
        email_domains=("deloitte.com",),
        company_type="Consulting",
    ),
    "ey": CompanyRecord(
        canonical_name="EY",
        aliases=("ernst & young", "ernst and young"),
        email_domains=("ey.com",),
        company_type="Consulting",
    ),
    "accenture": CompanyRecord(
        canonical_name="Accenture",
        aliases=("accenture india",),
        email_domains=("accenture.com",),
        company_type="Consulting",
    ),
    "fractal": CompanyRecord(
        canonical_name="Fractal",
        aliases=("fractal analytics",),
        email_domains=("fractal.ai",),
        company_type="AI Platforms",
    ),
    "turing": CompanyRecord(
        canonical_name="Turing",
        aliases=("turing.com",),
        email_domains=("turing.com",),
        company_type="AI Platforms",
    ),
    "observe.ai": CompanyRecord(
        canonical_name="Observe.AI",
        aliases=("observe ai",),
        email_domains=("observe.ai",),
        company_type="AI Platforms",
    ),
}


def is_noisy_company_label(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return True
    if _PLACEHOLDER_RE.match(v):
        return True
    if _NOISY_COMPANY_RE.match(v):
        return True
    return False


def _alias_index() -> list[tuple[str, CompanyRecord]]:
    rows: list[tuple[str, CompanyRecord]] = []
    for record in COMPANY_REGISTRY.values():
        rows.append((record.canonical_name.lower(), record))
        for alias in record.aliases:
            rows.append((alias.lower(), record))
    return sorted(rows, key=lambda x: -len(x[0]))


_ALIAS_INDEX = _alias_index()


def resolve_company_from_text(corpus: str) -> CompanyRecord | None:
    low = corpus.lower()
    for needle, record in _ALIAS_INDEX:
        if needle in low:
            return record
    return None


def resolve_company_from_email(corpus: str) -> CompanyRecord | None:
    for record in COMPANY_REGISTRY.values():
        for domain in record.email_domains:
            if domain in corpus.lower():
                return record
    match = re.search(r"[\w.+-]+@([\w.-]+\.\w+)", corpus)
    if match:
        domain = match.group(1).lower()
        for record in COMPANY_REGISTRY.values():
            if any(domain.endswith(d) for d in record.email_domains):
                return record
    return None


def resolve_company_from_line_hints(raw_text: str) -> str | None:
    for line in raw_text.splitlines()[:15]:
        cleaned = line.strip()
        if not cleaned or len(cleaned) > 90:
            continue
        if re.search(r"\b(inc|llc|ltd|limited|corp|corporation|technologies|global tech)\b", cleaned, re.I):
            rec = resolve_company_from_text(cleaned)
            if rec:
                return rec.canonical_name
            return cleaned.title().rstrip(".")
        if cleaned.endswith(":") and len(cleaned) < 45:
            return cleaned.rstrip(":").title()
    return None


def resolve_company(
    *,
    company: str,
    raw_text: str = "",
    title: str = "",
) -> tuple[str, list[str], str]:
    """
    Return (canonical_name, aliases, company_type).
    Never returns Unknown/null/tmp IDs.
    """
    if not is_noisy_company_label(company):
        rec = resolve_company_from_text(company)
        if rec:
            return rec.canonical_name, list(rec.aliases), rec.company_type
        return company.strip(), [], "Global Enterprise"

    corpus = f"{raw_text}\n{title}\n{company}"
    for resolver in (
        resolve_company_from_email,
        resolve_company_from_text,
    ):
        rec = resolver(corpus)
        if rec:
            return rec.canonical_name, list(rec.aliases), rec.company_type

    line_hint = resolve_company_from_line_hints(raw_text)
    if line_hint:
        rec = resolve_company_from_text(line_hint)
        if rec:
            return rec.canonical_name, list(rec.aliases), rec.company_type
        return line_hint, [], "Global Enterprise"

    return ENTERPRISE_FALLBACK_NAME, [], "Global Enterprise"


def list_registry_names() -> Iterable[str]:
    return (r.canonical_name for r in COMPANY_REGISTRY.values())
