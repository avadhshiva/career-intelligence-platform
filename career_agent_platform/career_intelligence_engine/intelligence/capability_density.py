"""Capability density scoring — recency, frequency, leadership context, ownership verbs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Ownership / leadership verb tiers (higher = stronger signal)
_OWNERSHIP_VERBS: dict[str, float] = {
    "led": 3.0,
    "owned": 3.0,
    "directed": 2.8,
    "governed": 2.8,
    "orchestrated": 2.6,
    "spearheaded": 2.5,
    "drove": 2.2,
    "managed": 2.0,
    "established": 2.0,
    "championed": 1.8,
    "facilitated": 1.5,
    "coordinated": 1.4,
    "supported": 0.8,
    "participated": 0.5,
    "assisted": 0.4,
    "contributed": 0.6,
}

_ENTERPRISE_SCOPE: dict[str, float] = {
    "enterprise-wide": 2.5,
    "enterprise wide": 2.5,
    "global matrix": 2.2,
    "fortune 500": 2.0,
    "multi-region": 1.8,
    "cross-bu": 2.0,
    "cross bu": 2.0,
    "organization-wide": 2.0,
    "org-wide": 1.8,
    "steering committee": 2.5,
    "governance board": 2.5,
    "executive reporting": 2.2,
    "portfolio governance": 2.0,
    "enterprise pmo": 2.0,
}

_OWNERSHIP_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(v) for v in _OWNERSHIP_VERBS) + r")\b",
    re.I,
)
_ENTERPRISE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _ENTERPRISE_SCOPE) + r")\b",
    re.I,
)
_LEADERSHIP_CONTEXT = re.compile(
    r"\b(executive|senior leadership|c-suite|board|vp|director|head of|"
    r"steering committee|governance board|portfolio|cross-functional)\b",
    re.I,
)


@dataclass
class CapabilityDensityResult:
    total_density: float
    ownership_score: float
    enterprise_scope_score: float
    leadership_context_score: float
    recency_score: float
    frequency_score: float
    matched_phrases: list[str] = field(default_factory=list)
    human_readable: list[str] = field(default_factory=list)


def _score_bullet(bullet: str, recency_weight: float) -> tuple[float, list[str]]:
    """Score a single bullet for capability density."""
    bullet_l = bullet.lower()
    score = 0.0
    phrases: list[str] = []

    for match in _OWNERSHIP_PATTERN.finditer(bullet):
        verb = match.group(1).lower()
        weight = _OWNERSHIP_VERBS.get(verb, 1.0)
        score += weight * recency_weight
        phrases.append(f"{verb} (weight {weight:.1f})")

    for match in _ENTERPRISE_PATTERN.finditer(bullet_l):
        scope = match.group(1).lower()
        weight = _ENTERPRISE_SCOPE.get(scope, 1.5)
        score += weight * recency_weight
        phrases.append(f"{scope} scope")

    leadership_hits = len(_LEADERSHIP_CONTEXT.findall(bullet_l))
    if leadership_hits:
        score += leadership_hits * 0.8 * recency_weight
        phrases.append("leadership context")

    return score, phrases


def score_capability_density(
    text: str,
    bullets: list[str] | None = None,
    *,
    family_signals: list[str] | None = None,
) -> CapabilityDensityResult:
    """
    Compute weighted capability density from resume text.

    Weights recency (recent bullets score higher), frequency, leadership context,
    enterprise scope, and ownership verbs.
    """
    bullets = bullets or []
    corpus = text.lower()
    all_phrases: list[str] = []
    bullet_scores: list[float] = []
    ownership_total = 0.0
    enterprise_total = 0.0
    leadership_total = 0.0

    for idx, bullet in enumerate(bullets):
        recency_weight = 1.5 if idx < 3 else (1.2 if idx < 6 else 1.0)
        b_score, phrases = _score_bullet(bullet, recency_weight)
        bullet_scores.append(b_score)
        all_phrases.extend(phrases)
        ownership_total += sum(
            _OWNERSHIP_VERBS.get(m.group(1).lower(), 1.0) * recency_weight
            for m in _OWNERSHIP_PATTERN.finditer(bullet)
        )
        enterprise_total += sum(
            _ENTERPRISE_SCOPE.get(m.group(1).lower(), 1.5) * recency_weight
            for m in _ENTERPRISE_PATTERN.finditer(bullet.lower())
        )
        leadership_total += len(_LEADERSHIP_CONTEXT.findall(bullet.lower())) * 0.8 * recency_weight

    # Frequency: count signal hits across corpus
    frequency_score = 0.0
    if family_signals:
        for sig in family_signals:
            sig_l = sig.lower()
            count = corpus.count(sig_l) + sum(b.lower().count(sig_l) for b in bullets)
            frequency_score += min(count, 5) * 0.3

    recency_score = min(1.0, sum(bullet_scores[:3]) / 15.0) if bullet_scores else 0.0
    ownership_norm = min(1.0, ownership_total / 12.0)
    enterprise_norm = min(1.0, enterprise_total / 10.0)
    leadership_norm = min(1.0, leadership_total / 8.0)
    frequency_norm = min(1.0, frequency_score / 5.0)

    total = min(
        1.0,
        ownership_norm * 0.30
        + enterprise_norm * 0.25
        + leadership_norm * 0.20
        + recency_score * 0.15
        + frequency_norm * 0.10,
    )

    human: list[str] = []
    if ownership_norm >= 0.4:
        human.append("Resume demonstrates strong ownership verbs (led, owned, directed, governed).")
    elif ownership_norm >= 0.15:
        human.append("Resume shows moderate ownership language in delivery contexts.")
    if enterprise_norm >= 0.35:
        human.append("Enterprise-wide scope signals detected (steering committee, governance board, cross-BU).")
    if leadership_norm >= 0.3:
        human.append("Leadership context appears in recent experience bullets.")
    if recency_score >= 0.4:
        human.append("Highest-density capability signals concentrate in recent roles.")

    return CapabilityDensityResult(
        total_density=round(total, 3),
        ownership_score=round(ownership_norm, 3),
        enterprise_scope_score=round(enterprise_norm, 3),
        leadership_context_score=round(leadership_norm, 3),
        recency_score=round(recency_score, 3),
        frequency_score=round(frequency_norm, 3),
        matched_phrases=all_phrases[:8],
        human_readable=human,
    )


def score_text_for_family(
    text: str,
    bullets: list[str],
    positive_signals: list[str],
    negative_signals: list[str] | None = None,
) -> float:
    """
    Score how well text matches a role family's signals with density weighting.

    Returns a non-normalized score suitable for role-family ranking.
    """
    density = score_capability_density(text, bullets, family_signals=positive_signals)
    corpus = text.lower()
    bullets_joined = "\n".join(bullets).lower()

    positive_hits = 0.0
    for sig in positive_signals:
        sig_l = sig.lower()
        in_text = sig_l in corpus or sig_l in bullets_joined
        if in_text:
            # Boost when signal appears with ownership verbs nearby
            boost = 1.0
            for bullet in bullets:
                if sig_l in bullet.lower():
                    b_score, _ = _score_bullet(bullet, 1.0)
                    boost = max(boost, 1.0 + b_score * 0.1)
            positive_hits += boost

    negative_hits = 0.0
    for sig in negative_signals or []:
        sig_l = sig.lower()
        if sig_l in corpus or sig_l in bullets_joined:
            negative_hits += 1.5

    base = positive_hits * (1.0 + density.total_density)
    return round(max(0.0, base - negative_hits), 3)
