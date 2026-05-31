from __future__ import annotations

from collections.abc import Iterable

from career_intelligence_engine.ontology.capability_vectors import DIMENSION_LABELS


def uniq(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        s = (raw or "").strip()
        if not s or s == "—" or s.lower() == "unknown":
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def top_n(items: Iterable[str], n: int) -> list[str]:
    return uniq(items)[: max(0, n)]


def humanize_dimensions(dim_ids: Iterable[str]) -> list[str]:
    return [DIMENSION_LABELS.get(d, d.replace("_", " ").title()) for d in uniq(dim_ids)]


def build_executive_summary(
    *,
    recruiter_summary: str | None,
    strengths: Iterable[str],
    gaps: Iterable[str],
    risks: Iterable[str],
) -> str:
    base = (recruiter_summary or "").strip()
    if base:
        return base

    s = top_n(strengths, 1)
    g = top_n(gaps, 1)
    r = top_n(risks, 1)

    parts: list[str] = []
    if s:
        parts.append(s[0].rstrip(".") + ".")
    if g:
        gap_text = g[0].rstrip(".")
        for prefix in ("main gap:", "gap area:", "gap dimension:"):
            if gap_text.lower().startswith(prefix):
                gap_text = gap_text.split(":", 1)[-1].strip()
        if gap_text.lower().startswith(("strategic ", "role expects", "profile is")):
            parts.append(gap_text + ".")
        else:
            parts.append(f"Primary development area: {gap_text}.")
    if r and not g:
        parts.append(f"Primary risk: {r[0].rstrip('.')}.")

    return " ".join(parts).strip() or "Fit assessment available. Review strengths and gaps below."


def _normalize_token(text: str) -> str:
    return " ".join((text or "").lower().split())


def _overlap_token(a: str, b: str, *, min_len: int = 24) -> bool:
    na = _normalize_token(a)
    nb = _normalize_token(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    return na[:min_len] in nb or nb[:min_len] in na


def lines_distinct_from_reference(
    reference: Iterable[str],
    candidates: Iterable[str],
) -> list[str]:
    """Drop candidate lines that substantially repeat reference bullets or summary."""
    refs = [_normalize_token(r) for r in uniq(reference) if r]
    out: list[str] = []
    for raw in uniq(candidates):
        token = _normalize_token(raw)
        if not token:
            continue
        if any(_overlap_token(token, ref) for ref in refs):
            continue
        if any(_overlap_token(token, prev) for prev in (_normalize_token(x) for x in out)):
            continue
        out.append(raw)
    return out


def strengths_distinct_from_summary(
    summary: str,
    strengths: Iterable[str],
) -> list[str]:
    """Drop strength bullets already covered by the positioning paragraph."""
    base = _normalize_token(summary)
    if not base:
        return uniq(strengths)

    out: list[str] = []
    for raw in uniq(strengths):
        token = _normalize_token(raw)
        if not token:
            continue
        if token in base or token[:48] in base:
            continue
        out.append(raw)
    return out

