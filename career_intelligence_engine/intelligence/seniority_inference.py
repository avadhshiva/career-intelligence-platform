"""Deterministic seniority inference from titles and tenure."""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_intelligence_engine.models.ontology import ParsedResume, SeniorityLevel

_SENIORITY_ORDER = [
    SeniorityLevel.INTERN,
    SeniorityLevel.JUNIOR,
    SeniorityLevel.MID,
    SeniorityLevel.SENIOR,
    SeniorityLevel.LEAD,
    SeniorityLevel.PRINCIPAL,
    SeniorityLevel.DIRECTOR,
    SeniorityLevel.VP,
    SeniorityLevel.C_LEVEL,
]

_TITLE_PATTERNS: list[tuple[re.Pattern[str], SeniorityLevel, float]] = [
    (re.compile(r"\b(intern|trainee)\b", re.I), SeniorityLevel.INTERN, 1.0),
    (re.compile(r"\b(junior|jr\.?|associate)\b", re.I), SeniorityLevel.JUNIOR, 0.9),
    (re.compile(r"\b(mid[- ]?level|ii)\b", re.I), SeniorityLevel.MID, 0.7),
    (re.compile(r"\b(senior|sr\.?)\b", re.I), SeniorityLevel.SENIOR, 0.95),
    (re.compile(r"\b(lead|staff)\b", re.I), SeniorityLevel.LEAD, 0.9),
    (re.compile(r"\b(principal|distinguished)\b", re.I), SeniorityLevel.PRINCIPAL, 0.95),
    (re.compile(r"\b(director|head of)\b", re.I), SeniorityLevel.DIRECTOR, 0.95),
    (re.compile(r"\b(vp|vice president|svp|evp)\b", re.I), SeniorityLevel.VP, 0.98),
    (
        re.compile(r"\b(ceo|cto|cfo|coo|chief|president)\b", re.I),
        SeniorityLevel.C_LEVEL,
        0.98,
    ),
]

_TENURE_SENIORITY: list[tuple[float, SeniorityLevel]] = [
    (0, SeniorityLevel.JUNIOR),
    (2, SeniorityLevel.MID),
    (5, SeniorityLevel.SENIOR),
    (8, SeniorityLevel.LEAD),
    (12, SeniorityLevel.PRINCIPAL),
    (15, SeniorityLevel.DIRECTOR),
]


@dataclass
class SeniorityResult:
    level: SeniorityLevel
    confidence: float
    signals: list[str]


class SeniorityInference:
    def infer(self, parsed: ParsedResume) -> SeniorityResult:
        scores: dict[SeniorityLevel, float] = {s: 0.0 for s in _SENIORITY_ORDER}
        signals: list[str] = []

        titles = parsed.job_titles or []
        recent = titles[0] if titles else ""
        search_titles = " | ".join(titles[:3])

        for pattern, level, weight in _TITLE_PATTERNS:
            if pattern.search(search_titles):
                scores[level] += weight
                signals.append(f"title_match:{level.value}")

        if parsed.years_experience is not None:
            tenure_level = self._tenure_to_seniority(parsed.years_experience)
            scores[tenure_level] += 0.5
            signals.append(
                f"tenure:{parsed.years_experience}y→{tenure_level.value}"
            )

        if recent and not any(scores[s] > 0 for s in scores):
            scores[SeniorityLevel.MID] += 0.3
            signals.append("default_mid_from_unlabeled_title")

        best = max(scores.items(), key=lambda x: x[1])
        if best[1] == 0:
            return SeniorityResult(SeniorityLevel.UNKNOWN, 0.0, signals)

        confidence = min(1.0, best[1] / 1.5)
        return SeniorityResult(best[0], round(confidence, 2), signals)

    def _tenure_to_seniority(self, years: float) -> SeniorityLevel:
        result = SeniorityLevel.JUNIOR
        for threshold, level in _TENURE_SENIORITY:
            if years >= threshold:
                result = level
        return result
