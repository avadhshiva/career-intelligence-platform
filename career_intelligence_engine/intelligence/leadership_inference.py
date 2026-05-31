"""Leadership maturity inference from management and scope signals."""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_intelligence_engine.models.ontology import LeadershipLevel, ParsedResume, SeniorityLevel

_PEOPLE_MANAGER = re.compile(
    r"\b(managed|leading a team|direct reports|people manager|"
    r"team of \d+|hired|coaching|performance reviews)\b",
    re.I,
)
_ORG_LEADER = re.compile(
    r"\b(org(?:anization)?(?:al)? leader|org-wide|department|"
    r"division|multi-team|matrix|executive stakeholder|"
    r"steering committee|board)\b",
    re.I,
)
_EXECUTIVE = re.compile(
    r"\b(c-suite|ceo|cto|cfo|executive sponsor|board of directors|"
    r"p&l|profit and loss|company-wide strategy)\b",
    re.I,
)
_TEAM_LEAD = re.compile(
    r"\b(tech lead|team lead|scrum master|chapter lead|"
    r"mentored|led engineers|led analysts)\b",
    re.I,
)
_IC_STRONG = re.compile(
    r"\b(individual contributor|hands-on|coded|implemented|"
    r"built from scratch|wrote)\b",
    re.I,
)


@dataclass
class LeadershipResult:
    level: LeadershipLevel
    governance_experience: float
    stakeholder_complexity: float
    execution_orientation: float
    strategic_orientation: float
    signals: list[str]


class LeadershipInference:
    def infer(
        self, parsed: ParsedResume, seniority: SeniorityLevel
    ) -> LeadershipResult:
        corpus = "\n".join(
            [parsed.raw_text]
            + parsed.bullets
            + parsed.job_titles
        )
        signals: list[str] = []
        score_map = {
            LeadershipLevel.INDIVIDUAL_CONTRIBUTOR: 0.0,
            LeadershipLevel.TEAM_LEAD: 0.0,
            LeadershipLevel.PEOPLE_MANAGER: 0.0,
            LeadershipLevel.ORG_LEADER: 0.0,
            LeadershipLevel.EXECUTIVE: 0.0,
        }

        if _IC_STRONG.search(corpus):
            score_map[LeadershipLevel.INDIVIDUAL_CONTRIBUTOR] += 0.6
            signals.append("ic_hands_on")
        if _TEAM_LEAD.search(corpus):
            score_map[LeadershipLevel.TEAM_LEAD] += 0.8
            signals.append("team_lead_scope")
        if _PEOPLE_MANAGER.search(corpus):
            score_map[LeadershipLevel.PEOPLE_MANAGER] += 1.0
            signals.append("people_management")
        if _ORG_LEADER.search(corpus):
            score_map[LeadershipLevel.ORG_LEADER] += 1.0
            signals.append("org_scope")
        if _EXECUTIVE.search(corpus):
            score_map[LeadershipLevel.EXECUTIVE] += 1.0
            signals.append("executive_scope")

        # Seniority prior
        if seniority in (SeniorityLevel.DIRECTOR, SeniorityLevel.VP, SeniorityLevel.C_LEVEL):
            score_map[LeadershipLevel.ORG_LEADER] += 0.5
            score_map[LeadershipLevel.EXECUTIVE] += 0.3
            signals.append(f"seniority_prior:{seniority.value}")
        elif seniority in (SeniorityLevel.SENIOR, SeniorityLevel.LEAD, SeniorityLevel.PRINCIPAL):
            score_map[LeadershipLevel.TEAM_LEAD] += 0.3
            score_map[LeadershipLevel.PEOPLE_MANAGER] += 0.2

        best = max(score_map.items(), key=lambda x: x[1])
        level = best[0] if best[1] > 0 else LeadershipLevel.UNKNOWN

        governance = self._clamp(self._count_weighted(corpus, _ORG_LEADER) * 0.25 + 0.1)
        stakeholder = self._clamp(
            self._count_weighted(corpus, _EXECUTIVE) * 0.2
            + self._count_weighted(corpus, _ORG_LEADER) * 0.15
            + 0.1
        )
        execution = self._clamp(
            self._count_weighted(corpus, _IC_STRONG) * 0.15
            + self._count_weighted(corpus, _TEAM_LEAD) * 0.1
            + 0.35
        )
        strategic = self._clamp(
            self._count_weighted(corpus, _EXECUTIVE) * 0.2
            + self._count_weighted(corpus, _ORG_LEADER) * 0.15
            + (0.2 if seniority.value in ("director", "vp", "c_level") else 0.05)
        )

        return LeadershipResult(
            level=level,
            governance_experience=round(governance, 2),
            stakeholder_complexity=round(stakeholder, 2),
            execution_orientation=round(execution, 2),
            strategic_orientation=round(strategic, 2),
            signals=signals,
        )

    def _count_weighted(self, text: str, pattern: re.Pattern[str]) -> float:
        return min(1.0, len(pattern.findall(text)) * 0.2)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
