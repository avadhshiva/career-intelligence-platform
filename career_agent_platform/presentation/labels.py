from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Badge:
    label: str
    tone: str  # streamlit-ish semantic: success/info/warning/error/secondary


_MATCH_CATEGORY_BADGES: dict[str, Badge] = {
    "STRONG_MATCH": Badge("Strong Match", "success"),
    "GOOD_MATCH": Badge("Good Match", "info"),
    "BORDERLINE": Badge("Moderate Alignment", "warning"),
    "LOW_MATCH": Badge("Limited Fit", "secondary"),
}


def match_category_badge(value: str | None) -> Badge:
    if not value:
        return Badge("Needs Review", "secondary")
    return _MATCH_CATEGORY_BADGES.get(str(value), Badge("Needs Review", "secondary"))


def discourages_primary_approve(
    *,
    eligibility_passed: bool,
    recommendation_priority: str | None,
) -> bool:
    """Roles that should not surface a primary Approve CTA."""
    if not eligibility_passed:
        return True
    priority = str(recommendation_priority or "").upper()
    return priority in ("LOW_MATCH", "BORDERLINE")


def format_location(value: str | None) -> str:
    if not value:
        return ""
    v = str(value).strip()
    if not v or v.lower() == "unknown":
        return ""
    return v


def safe_company(value: str | None) -> str:
    from job_sources.normalization import infer_company

    v = (value or "").strip()
    if not v or v.lower() == "unknown":
        return "Company"
    inferred = infer_company(company=v, raw_text="")
    return inferred if inferred != "Enterprise Employer" else v


def safe_title(value: str | None) -> str:
    from job_sources.normalization import infer_title

    v = (value or "").strip()
    if not v or v.lower() == "unknown":
        return "Role"
    return infer_title(title=v, raw_text="")


def role_metadata_line(
    *,
    company: str | None,
    location: str | None,
    badge_label: str,
) -> str:
    """Executive subline: Company • Location • Match tier."""
    parts: list[str] = []
    co = safe_company(company)
    if co != "Company":
        parts.append(co)
    loc = format_location(location)
    if loc:
        parts.append(loc)
    if badge_label:
        parts.append(badge_label)
    return " • ".join(parts) if parts else badge_label

