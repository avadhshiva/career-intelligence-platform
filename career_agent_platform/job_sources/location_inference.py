"""Deterministic location and remote-work inference."""

from __future__ import annotations

import re
from dataclasses import dataclass

from job_sources.title_normalization import is_noisy_title

_LOCATION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bbengaluru\b|\bbangalore\b", "Bangalore"),
    (r"\bhyderabad\b", "Hyderabad"),
    (r"\bchennai\b", "Chennai"),
    (r"\bpune\b", "Pune"),
    (r"\bmumbai\b", "Mumbai"),
    (r"\bdelhi\b|\bncr\b|\bgurgaon\b|\bgurugram\b|\bnoida\b", "Delhi NCR"),
    (r"\bcoimbatore\b", "Coimbatore"),
    (r"\blondon\b", "London"),
    (r"\bseattle\b", "Seattle"),
    (r"\bsan francisco\b|\bsf bay\b|\bbay area\b", "San Francisco Bay Area"),
    (r"\bnew york\b|\bnyc\b", "New York"),
    (r"\bchicago\b", "Chicago"),
    (r"\baustin\b", "Austin"),
    (r"\bdallas\b", "Dallas"),
)


@dataclass(frozen=True)
class LocationInferenceResult:
    location: str
    remote_type: str


def _search_patterns(text: str, patterns: tuple[tuple[str, str], ...]) -> str:
    low = text.lower()
    for pattern, label in patterns:
        if re.search(pattern, low):
            return label
    return ""


def infer_remote_type(*, location: str, raw_text: str) -> str:
    low = f"{location}\n{raw_text}".lower()
    if re.search(r"\bglobal remote\b|\bworldwide remote\b", low):
        return "Global Remote"
    if re.search(r"\bus remote\b|\bunited states remote\b", low):
        return "US Remote"
    if "remote" in low and "hybrid" in low:
        return "Hybrid"
    if re.search(r"\bremote\b|\bwork from home\b|\bwfh\b", low):
        return "Remote"
    if "hybrid" in low:
        return "Hybrid"
    if re.search(r"\bon-?site\b|\boffice-?based\b", low):
        return "On-site"
    return "Flexible"


def infer_location(
    *,
    location: str = "",
    raw_text: str = "",
) -> LocationInferenceResult:
    loc = (location or "").strip()
    if loc and not is_noisy_title(loc) and loc.lower() not in {"unknown", "location flexible"}:
        city = loc
    else:
        city = _search_patterns(raw_text, _LOCATION_PATTERNS)

    remote = infer_remote_type(location=city or loc, raw_text=raw_text)

    if not city:
        if remote in {"Remote", "Global Remote", "US Remote"}:
            city = remote
        elif remote == "Hybrid":
            city = _search_patterns(raw_text, _LOCATION_PATTERNS) or "Hybrid"
        else:
            city = "Location Flexible"

    return LocationInferenceResult(location=city, remote_type=remote)


def location_display_line(location: str, remote_type: str) -> str:
    if remote_type in {"Hybrid", "Remote", "Global Remote", "US Remote"} and location not in {
        remote_type,
        "Location Flexible",
    }:
        return f"{location} • {remote_type}"
    if remote_type == "Hybrid" and location == "Hybrid":
        return "Hybrid"
    return location
