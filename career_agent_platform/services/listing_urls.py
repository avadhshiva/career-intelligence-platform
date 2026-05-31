"""Deterministic LinkedIn job search URLs from normalized entity fields (no scraping).

Trust requirements:
- Never emit malformed URLs
- Never emit placeholder/example domains
- Never reuse stale LinkedIn job IDs, currentJobId, or synthetic identifiers
- Always build clean search URLs from normalized_title, company_name, and location
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

_PLACEHOLDER_HOSTS = ("careers.example.com", "example.com")

_MAX_QUERY_TOKENS = 12
_MAX_QUERY_CHARS = 120

_BROKEN_QUERY_KEYS = frozenset(
    {
        "currentjobid",
        "jobid",
        "f_c",
        "f_e",
        "f_tpr",
        "f_wt",
        "origin",
        "refid",
        "trackingid",
    }
)

_SYNTHETIC_ID_PATTERN = re.compile(
    r"(?:^|[/?&=])(?:currentJobId|jobId|refId|trackingId|preview|sample|tmp|demo)[=/_-]?[\w-]*",
    re.IGNORECASE,
)


def is_placeholder_url(url: str) -> bool:
    lower = (url or "").lower()
    return not lower or any(host in lower for host in _PLACEHOLDER_HOSTS)


def _clean_text(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = re.sub(r"\s+", " ", raw).strip()
    if raw.lower() in {"n/a", "na", "none", "null", "unknown", "--"}:
        return ""
    return raw


def _trim_query(query: str) -> str:
    q = _clean_text(query)
    if not q:
        return ""
    tokens = q.split()
    if len(tokens) > _MAX_QUERY_TOKENS:
        tokens = tokens[:_MAX_QUERY_TOKENS]
    q = " ".join(tokens).strip()
    if len(q) > _MAX_QUERY_CHARS:
        q = q[:_MAX_QUERY_CHARS].rstrip()
    return q


def is_broken_listing_url(url: str) -> bool:
    """True when a URL must not be reused (stale IDs, view links, placeholders)."""
    candidate = (url or "").strip()
    if not candidate or is_placeholder_url(candidate):
        return True
    if _SYNTHETIC_ID_PATTERN.search(candidate):
        return True
    try:
        parsed = urlparse(candidate)
    except Exception:
        return True
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return True
    host = parsed.netloc.lower()
    if "linkedin.com" not in host:
        return False
    path = (parsed.path or "").lower()
    if path.startswith("/jobs/view/") or "/jobs/view/" in path:
        return True
    if not path.startswith("/jobs/search"):
        return True
    qs = parse_qs(parsed.query or "")
    for key in qs:
        if key.lower() in _BROKEN_QUERY_KEYS:
            return True
    keywords = (qs.get("keywords") or [""])[0].strip()
    if not keywords or keywords.lower() in {"none", "null"}:
        return True
    return False


def build_linkedin_search_url(
    *,
    normalized_title: str,
    company_name: str = "",
    location: str = "",
) -> str:
    """Build a clean LinkedIn jobs search URL from normalized entity fields only."""
    title = _trim_query(normalized_title)
    company = _trim_query(company_name)
    loc = _trim_query(location)

    if company:
        keywords = _trim_query(f"{title} {company}".strip()) if title else company
    else:
        keywords = title

    if not keywords:
        return ""

    url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keywords)}"
    if loc:
        url += f"&location={quote_plus(loc)}"
    return url


def build_valid_listing_url(title: str, company: str, location: str) -> str:
    """Backward-compatible wrapper for normalized entity fields."""
    return build_linkedin_search_url(
        normalized_title=title,
        company_name=company,
        location=location,
    )


def resolve_listing_url(
    *,
    company: str,
    role: str,
    location: str = "",
    job_url: str = "",
    normalized_title: str = "",
    company_name: str = "",
) -> str:
    """Always derive a fresh LinkedIn search URL; never reuse cached/broken links."""
    _ = job_url  # ignored — URLs are always rebuilt from normalized entity fields
    title = _clean_text(normalized_title) or _clean_text(role)
    org = _clean_text(company_name) or _clean_text(company)
    loc = _clean_text(location)
    built = build_linkedin_search_url(
        normalized_title=title,
        company_name=org,
        location=loc,
    )
    return built if built and not is_broken_listing_url(built) else ""


def scrub_persisted_listing_urls(data_dir: Path) -> int:
    """Remove cached listing URLs from queue/package snapshots so they are rebuilt at runtime."""
    removed = 0
    if not data_dir.exists():
        return removed

    for path in sorted(data_dir.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        changed = False

        def _scrub_obj(obj: object) -> None:
            nonlocal changed, removed
            if isinstance(obj, dict):
                for key in list(obj.keys()):
                    if key in {"job_url", "listing_url"} and isinstance(obj[key], str):
                        del obj[key]
                        removed += 1
                        changed = True
                    else:
                        _scrub_obj(obj[key])
            elif isinstance(obj, list):
                for item in obj:
                    _scrub_obj(item)

        _scrub_obj(payload)
        if changed:
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return removed
