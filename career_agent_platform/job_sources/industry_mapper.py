"""Industry clustering from company profile and JD language."""

from __future__ import annotations

import re
from typing import Iterable

from job_sources.company_registry import CompanyRecord

# JD keyword → industry label (deterministic)
_JD_INDUSTRY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bretail\b|\be-?commerce\b|\bstore operations\b|\bomnichannel\b", "Retail Tech"),
    (r"\bfintech\b|\bbanking\b|\bcapital markets\b|\binsurance\b|\bfinancial services\b", "FinTech"),
    (r"\bconsulting\b|\bprofessional services\b|\badvisory\b", "Consulting"),
    (r"\bsaas\b|\benterprise software\b|\bplatform company\b", "Enterprise SaaS"),
    (r"\bcloud\b|\baws\b|\bazure\b|\bgcp\b", "Cloud Platforms"),
    (r"\bai platform\b|\bml platform\b|\bgenai\b|\blarge language model\b", "AI Platforms"),
    (r"\bsupply chain\b|\blogistics\b|\bfulfillment\b", "Supply Chain"),
    (r"\bhealthcare\b|\blife sciences\b|\bpharma\b", "Healthcare"),
)

_COMPANY_TYPE_TO_INDUSTRY: dict[str, str] = {
    "Retail Tech": "Retail Tech",
    "Banking": "FinTech",
    "FinTech": "FinTech",
    "Consulting": "Consulting",
    "Enterprise SaaS": "Enterprise SaaS",
    "Cloud Platforms": "Cloud Platforms",
    "AI Platforms": "AI Platforms",
    "Global Enterprise": "Enterprise Technology",
}


def _search_patterns(text: str, patterns: tuple[tuple[str, str], ...]) -> str:
    low = text.lower()
    for pattern, label in patterns:
        if re.search(pattern, low):
            return label
    return ""


def infer_industry_from_jd(raw_text: str) -> str:
    return _search_patterns(raw_text, _JD_INDUSTRY_PATTERNS) or ""


def infer_industry(
    *,
    company_type: str,
    company_name: str,
    raw_text: str,
) -> str:
    from_jd = infer_industry_from_jd(raw_text)
    if from_jd:
        return from_jd
    if company_type in _COMPANY_TYPE_TO_INDUSTRY:
        mapped = _COMPANY_TYPE_TO_INDUSTRY[company_type]
        if mapped != "Enterprise Technology" or not company_name:
            return mapped
    corpus = f"{company_name}\n{raw_text[:1500]}".lower()
    if "retail" in corpus or "walmart" in corpus or "target" in corpus:
        return "Retail Tech"
    if "bank" in corpus or "jpmorgan" in corpus or "lseg" in corpus:
        return "FinTech"
    return "Enterprise Technology"


def industry_chip_label(industry: str) -> str:
    return industry or "Enterprise Technology"
