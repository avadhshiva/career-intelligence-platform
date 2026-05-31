"""Title normalization — abbreviations, seniority, role family, leadership."""

from __future__ import annotations

import re
from dataclasses import dataclass

_NOISY_TITLE_RE = re.compile(r"^tmp[a-z0-9]{4,}$", re.IGNORECASE)
_UUIDISH_RE = re.compile(r"^[a-f0-9-]{8,}$", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"^(unknown|role|untitled|n/a)$", re.I)

_ABBREVIATION_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\bsr\.?\b", "Senior"),
    (r"\bjr\.?\b", "Junior"),
    (r"\bdir\.?\b", "Director"),
    (r"\bvp\b", "Vice President"),
    (r"\bsvp\b", "Senior Vice President"),
    (r"\bprog\.?\b", "Program"),
    (r"\bmgmt\b", "Management"),
    (r"\bmgr\b", "Manager"),
    (r"\btpm\b", "Technical Program Manager"),
    (r"\bpm\b", "Program Manager"),
    (r"\bai/ml\b", "AI/ML"),
    (r"\bgenai\b", "GenAI"),
    (r"\brte\b", "Release Train Engineer"),
    (r"\bsdlc\b", "SDLC"),
)

_ROLE_FAMILY_FROM_TEXT: tuple[tuple[str, str], ...] = (
    (r"\bai transformation\b|\bai strategy\b|\bgenai\b|\bresponsible ai\b", "ai_transformation"),
    (r"\bai program\b|\bmlops\b|\bai governance\b", "ai_program_management"),
    (r"\btechnical program\b|\btpm\b|\bengineering program\b", "technical_program_management"),
    (r"\brelease governance\b|\brelease train\b|\bpi planning\b", "release_governance"),
    (r"\benterprise delivery\b|\bprogram delivery\b|\bpmo\b", "enterprise_delivery"),
    (r"\bproduct manager\b|\bproduct owner\b|\bproduct management\b", "product_management"),
    (r"\benterprise architect\b|\barchitecture lead\b", "enterprise_architecture_delivery"),
    (r"\btransformation office\b|\bdigital transformation\b", "digital_transformation"),
    (r"\bcloud transformation\b|\bcloud migration\b", "cloud_transformation"),
    (r"\bprogram director\b|\bportfolio\b|\bprogram lead\b", "program_leadership"),
)

_TITLE_FALLBACK_BY_FAMILY: dict[str, str] = {
    "ai_transformation": "AI Transformation Leadership Opportunity",
    "ai_program_management": "AI Program Leadership Opportunity",
    "technical_program_management": "Technical Program Management Opportunity",
    "release_governance": "Release Governance Leadership Opportunity",
    "enterprise_delivery": "Enterprise Delivery Leadership Opportunity",
    "product_management": "Product Leadership Opportunity",
    "enterprise_architecture_delivery": "Enterprise Architecture Leadership Opportunity",
    "digital_transformation": "Transformation Leadership Opportunity",
    "cloud_transformation": "Cloud Transformation Leadership Opportunity",
    "program_leadership": "Enterprise Program Leadership Opportunity",
}

_SENIORITY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(c-level|chief|ceo|cto|cio)\b", "Executive"),
    (r"\b(vp|vice president|svp)\b", "Executive"),
    (r"\b(director|head of)\b", "Director"),
    (r"\b(principal|distinguished)\b", "Principal"),
    (r"\b(senior manager|sr manager)\b", "Senior Manager"),
    (r"\b(manager|lead)\b", "Manager"),
    (r"\b(senior|sr)\b", "Senior"),
)

_LEADERSHIP_FROM_SENIORITY: dict[str, str] = {
    "Executive": "executive",
    "Director": "org_leader",
    "Principal": "org_leader",
    "Senior Manager": "people_manager",
    "Manager": "people_manager",
    "Senior": "team_lead",
}


@dataclass(frozen=True)
class TitleNormalizationResult:
    normalized_title: str
    raw_title: str
    inferred_role_family: str
    inferred_seniority: str
    inferred_leadership_level: str


def is_noisy_title(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return True
    if _PLACEHOLDER_RE.match(v.lower()):
        return True
    if _NOISY_TITLE_RE.match(v):
        return True
    if _UUIDISH_RE.match(v) and " " not in v:
        return True
    if re.match(r"^[a-z0-9_-]{6,}$", v, re.I) and not any(c.isupper() for c in v[1:]):
        return True
    return False


def _search_patterns(text: str, patterns: tuple[tuple[str, str], ...]) -> str:
    low = text.lower()
    for pattern, label in patterns:
        if re.search(pattern, low):
            return label
    return ""


def expand_abbreviations(title: str) -> str:
    result = title.strip()
    for pattern, replacement in _ABBREVIATION_REPLACEMENTS:
        result = re.sub(pattern, replacement, result, flags=re.I)
    result = re.sub(r"\s+", " ", result).strip()
    result = re.sub(r"\s*-\s*", " - ", result)
    return result.title() if result.isupper() or result.islower() else result


def infer_role_family(*, title: str, raw_text: str, hint: str = "") -> str:
    if hint:
        return hint
    corpus = f"{title}\n{raw_text[:3000]}"
    found = _search_patterns(corpus, _ROLE_FAMILY_FROM_TEXT)
    return found or "enterprise_delivery"


def infer_seniority(*, title: str, raw_text: str) -> str:
    corpus = f"{title}\n{raw_text[:2000]}"
    return _search_patterns(corpus, _SENIORITY_PATTERNS) or "Senior"


def infer_leadership_level(seniority: str) -> str:
    return _LEADERSHIP_FROM_SENIORITY.get(seniority, "individual_contributor")


def normalize_title(
    *,
    title: str,
    raw_text: str = "",
    role_family_hint: str = "",
) -> TitleNormalizationResult:
    raw = (title or "").strip()
    role_family = infer_role_family(title=raw, raw_text=raw_text, hint=role_family_hint)

    if is_noisy_title(raw):
        fallback = _TITLE_FALLBACK_BY_FAMILY.get(
            role_family,
            "Enterprise Program Leadership Opportunity",
        )
        corpus_family = infer_role_family(title="", raw_text=raw_text, hint="")
        if corpus_family != "enterprise_delivery":
            role_family = corpus_family
            fallback = _TITLE_FALLBACK_BY_FAMILY.get(role_family, fallback)
        seniority = infer_seniority(title=fallback, raw_text=raw_text)
        return TitleNormalizationResult(
            normalized_title=fallback,
            raw_title=raw,
            inferred_role_family=role_family,
            inferred_seniority=seniority,
            inferred_leadership_level=infer_leadership_level(seniority),
        )

    expanded = expand_abbreviations(raw)
    seniority = infer_seniority(title=expanded, raw_text=raw_text)
    return TitleNormalizationResult(
        normalized_title=expanded,
        raw_title=raw,
        inferred_role_family=role_family,
        inferred_seniority=seniority,
        inferred_leadership_level=infer_leadership_level(seniority),
    )
