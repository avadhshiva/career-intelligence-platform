"""UI-only sanitization — filters placeholders and internal jargon for display."""

from __future__ import annotations

import re
from collections.abc import Iterable

from presentation.explainability import humanize_dimensions, uniq
from presentation.labels import safe_company, safe_title

_PLACEHOLDER_TOKENS = frozenset(
    {
        "",
        "—",
        "-",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "tbd",
        "todo",
        "placeholder",
        "tmp",
        "lorem ipsum",
    }
)

_META_SUBSTRINGS = (
    "deterministic_job_match_v1",
    "derived from deterministic",
    "deterministic match score",
    "deterministic review of my documented",
    "deterministic emphasis",
    "sourced from overall_match",
    "weighted blend of alignment",
    "capability vector similarity",
    "hard eligibility gates",
)

_JOB_WEIGHT_RE = re.compile(
    r"\(job weight\s+\d+%\)",
    re.IGNORECASE,
)

_TMP_TITLE_RE = re.compile(r"^tmp[\w\-]*$", re.IGNORECASE)


def is_placeholder_text(value: str | None) -> bool:
    if value is None:
        return True
    v = str(value).strip()
    if not v:
        return True
    if v.lower() in _PLACEHOLDER_TOKENS:
        return True
    if _TMP_TITLE_RE.match(v):
        return True
    if v.lower().startswith("tmp") and len(v) <= 24:
        return True
    return False


def sanitize_display_text(value: str | None) -> str:
    """Return cleaned user-facing text, or empty string if not displayable."""
    if is_placeholder_text(value):
        return ""
    text = str(value).strip()
    for phrase in _META_SUBSTRINGS:
        if phrase in text.lower():
            text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
    text = _JOB_WEIGHT_RE.sub("", text)
    text = re.sub(
        r"Strong alignment on\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s{2,}", " ", text).strip(" .,-")
    return text if not is_placeholder_text(text) else ""


def sanitize_bullet_list(items: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        line = humanize_gap_line(str(item))
        if not line:
            line = sanitize_display_text(str(item))
        if line:
            cleaned.append(line)
    return uniq(cleaned)


def sanitize_artifact_prose(
    text: str,
    *,
    job_title: str | None = None,
    company: str | None = None,
) -> str:
    """Clean generated artifact text for UI (tmp titles, unknown company, jargon)."""
    out = sanitize_display_text(text)
    if not out:
        return ""

    raw_title = (job_title or "").strip()
    raw_company = (company or "").strip()
    display_title = safe_title(job_title)
    display_company = safe_company(company)

    if raw_title and (is_placeholder_text(raw_title) or display_title == "Role"):
        out = re.sub(re.escape(raw_title), "the role", out, flags=re.IGNORECASE)
    out = re.sub(r"\bTmp[\w]+\b", "the role", out, flags=re.IGNORECASE)

    if is_placeholder_text(raw_company) or raw_company.lower() == "unknown":
        if raw_company:
            out = re.sub(re.escape(raw_company), display_company, out, flags=re.IGNORECASE)
        out = re.sub(r"\bat Unknown\b", f"at {display_company}", out, flags=re.IGNORECASE)

    if display_title == "Role":
        out = re.sub(r"\bthe the role\b", "the role", out, flags=re.IGNORECASE)
        out = re.sub(r"\bthe role role\b", "this role", out, flags=re.IGNORECASE)
        out = re.sub(r"\bthe role opportunity\b", "this opportunity", out, flags=re.IGNORECASE)
        out = re.sub(r"\bthe role position\b", "this role", out, flags=re.IGNORECASE)
        out = re.sub(r"\binterested in the role position\b", "interested in this role", out, flags=re.IGNORECASE)

    return sanitize_display_text(out) or out


def sanitize_gap_question(question: str) -> str:
    q = sanitize_display_text(question)
    if not q:
        return ""
    if q.endswith(": ?"):
        return ""
    if q.lower().startswith("how would you address:") and is_placeholder_text(
        q.split(":", 1)[-1].strip().rstrip("?"),
    ):
        return ""
    if q.lower().startswith("tell me about your experience with"):
        topic = q.split("with", 1)[-1].strip().rstrip(".")
        if is_placeholder_text(topic):
            return ""
    return q


def humanize_gap_line(line: str) -> str:
    cleaned = sanitize_display_text(line)
    if not cleaned:
        return ""
    if cleaned.lower().startswith("gap dimension:"):
        dim = cleaned.split(":", 1)[-1].strip()
        labels = humanize_dimensions([dim])
        return f"Gap area: {labels[0]}" if labels else ""
    return cleaned


def format_score_percent(
    score: float | None,
    *,
    fallback: float | None = None,
) -> str:
    """Format 0–1 score for metrics; never show misleading 0% when data is absent."""
    candidate = score if _is_meaningful_score(score) else fallback
    if not _is_meaningful_score(candidate):
        return "—"
    return f"{int(round(float(candidate) * 100))}%"


def _is_meaningful_score(value: float | None) -> bool:
    return value is not None and float(value) > 0.0


def resolve_snapshot_scores(
    snapshot: dict | None,
    *,
    package_confidence: float | None = None,
    resume_alignment: float | None = None,
) -> tuple[str, str]:
    """Fit and confidence labels from recommendation snapshot with safe fallbacks."""
    snap = snapshot or {}
    raw_match = snap.get("overall_match")
    raw_conf = snap.get("confidence")

    match_fallback = resume_alignment if _is_meaningful_score(resume_alignment) else None
    conf_fallback = package_confidence if _is_meaningful_score(package_confidence) else None

    fit = format_score_percent(
        float(raw_match) if raw_match is not None else None,
        fallback=match_fallback,
    )
    conf = format_score_percent(
        float(raw_conf) if raw_conf is not None else None,
        fallback=conf_fallback,
    )
    return fit, conf
