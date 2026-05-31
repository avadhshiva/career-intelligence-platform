"""Executive signal detection — governance boards, steering committees, enterprise PMO."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from career_intelligence_engine.models.ontology import ParsedResume

_GOVERNANCE_BOARD = re.compile(
    r"\b(governance board|architecture review board|model governance board|"
    r"portfolio governance|release governance board|ai governance council)\b",
    re.I,
)
_EXECUTIVE_CADENCE = re.compile(
    r"\b(executive steering|steering committee|executive committee|"
    r"quarterly business review|qbr|executive reporting|"
    r"c-suite|board of directors|executive sponsor)\b",
    re.I,
)
_ENTERPRISE_PMO = re.compile(
    r"\b(enterprise pmo|global pmo|program management office|"
    r"portfolio office|transformation office|tmo)\b",
    re.I,
)
_PORTFOLIO_GOVERNANCE = re.compile(
    r"\b(portfolio governance|benefits realization|value realization|"
    r"investment committee|prioritization framework|funding governance)\b",
    re.I,
)
_ORG_TRANSFORMATION = re.compile(
    r"\b(organizational transformation|operating model redesign|"
    r"enterprise transformation|business transformation|"
    r"org redesign|target operating model)\b",
    re.I,
)
_AI_STRATEGY_OWNERSHIP = re.compile(
    r"\b(ai strategy|ai roadmap|ai transformation|genai strategy|"
    r"responsible ai framework|ai center of excellence|ai coe)\b",
    re.I,
)
_CROSS_BU = re.compile(
    r"\b(cross-bu|cross bu|cross-business unit|global matrix|"
    r"multi-geography|multi-region|enterprise-wide|enterprise wide)\b",
    re.I,
)


@dataclass
class ExecutiveSignalResult:
    executive_strength: float
    transformation_leadership: float
    enterprise_governance: float
    signals: list[str] = field(default_factory=list)
    human_readable: list[str] = field(default_factory=list)


def _count_pattern(text: str, pattern: re.Pattern[str]) -> int:
    return len(pattern.findall(text))


def detect_executive_signals(parsed: ParsedResume) -> ExecutiveSignalResult:
    """
    Infer executive-level signals from resume text.

    Returns executive_strength, transformation_leadership, and enterprise_governance
    scores (0–1) plus structured and human-readable signal lists.
    """
    corpus = "\n".join([parsed.raw_text] + parsed.bullets + parsed.job_titles)
    signals: list[str] = []
    human: list[str] = []

    gov_board = _count_pattern(corpus, _GOVERNANCE_BOARD)
    exec_cadence = _count_pattern(corpus, _EXECUTIVE_CADENCE)
    enterprise_pmo = _count_pattern(corpus, _ENTERPRISE_PMO)
    portfolio_gov = _count_pattern(corpus, _PORTFOLIO_GOVERNANCE)
    org_transform = _count_pattern(corpus, _ORG_TRANSFORMATION)
    ai_strategy = _count_pattern(corpus, _AI_STRATEGY_OWNERSHIP)
    cross_bu = _count_pattern(corpus, _CROSS_BU)

    enterprise_governance = min(
        1.0,
        0.08
        + gov_board * 0.18
        + exec_cadence * 0.15
        + enterprise_pmo * 0.12
        + portfolio_gov * 0.14
        + cross_bu * 0.10,
    )

    ai_strategy_weight = 0.16 if ai_strategy >= 3 else (0.08 if ai_strategy >= 2 else 0.04)
    transformation_leadership = min(
        1.0,
        0.06
        + org_transform * 0.20
        + ai_strategy * ai_strategy_weight
        + portfolio_gov * 0.10
        + exec_cadence * 0.08,
    )

    executive_strength = min(
        1.0,
        0.10
        + exec_cadence * 0.20
        + gov_board * 0.15
        + cross_bu * 0.12
        + enterprise_pmo * 0.10
        + (0.08 if org_transform >= 1 else 0.0),
    )

    if gov_board >= 1:
        signals.append("governance_board")
        human.append("Resume references governance board or council participation.")
    if exec_cadence >= 1:
        signals.append("executive_cadence")
        human.append("Executive cadence signals present (steering committee, executive reporting).")
    if enterprise_pmo >= 1:
        signals.append("enterprise_pmo")
        human.append("Enterprise PMO or transformation office scope indicated.")
    if portfolio_gov >= 1:
        signals.append("portfolio_governance")
        human.append("Portfolio governance and benefits realization language detected.")
    if org_transform >= 1:
        signals.append("organizational_transformation")
        human.append("Organizational transformation and operating model change evidence.")
    if ai_strategy >= 2:
        signals.append("ai_strategy_ownership")
        human.append("Resume contains repeated enterprise AI strategy ownership signals.")
    elif ai_strategy >= 1:
        signals.append("ai_strategy_awareness")
        human.append("AI strategy and roadmap ownership language present.")
    if cross_bu >= 1:
        signals.append("cross_bu_leadership")
        human.append("Cross-BU or enterprise-wide leadership scope demonstrated.")

    if enterprise_governance >= 0.5 and not any("governance" in h.lower() for h in human):
        human.append(
            "Candidate demonstrates large-enterprise governance and cross-functional delivery language."
        )

    return ExecutiveSignalResult(
        executive_strength=round(executive_strength, 3),
        transformation_leadership=round(transformation_leadership, 3),
        enterprise_governance=round(enterprise_governance, 3),
        signals=signals,
        human_readable=human,
    )
