"""Domain and enterprise exposure inference."""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_intelligence_engine.models.ontology import EnterpriseExposure, ParsedResume
from career_intelligence_engine.ontology.company_archetypes import COMPANY_ARCHETYPES
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from career_intelligence_engine.models.ontology import CompanyArchetypeId, RoleFamilyId

_ENTERPRISE_SIGNALS = re.compile(
    r"\b(fortune|global enterprise|multinational|matrix|"
    r"enterprise-wide|10,?000\+?\s*employees|ftse|global 2000)\b",
    re.I,
)
_MODERATE_ENTERPRISE = re.compile(
    r"\b(mid-market|regional|pmo|governance|steering committee|"
    r"cross-region|multi-site)\b",
    re.I,
)
_DELIVERY_SIGNALS = re.compile(
    r"\b(delivery|implementation|rollout|deployment|milestone|"
    r"runbook|cutover|uat|hypercare)\b",
    re.I,
)


@dataclass
class DomainResult:
    primary_domains: list[str]
    secondary_domains: list[str]
    enterprise_experience: EnterpriseExposure
    delivery_orientation: float
    company_archetypes: list[CompanyArchetypeId]
    signals: list[str]


class DomainInference:
    def infer(
        self,
        parsed: ParsedResume,
        skill_domains: dict[str, list[str]],
    ) -> DomainResult:
        corpus = parsed.raw_text.lower()
        signals: list[str] = []

        primary = list(skill_domains.get("primary_domains", []))
        secondary = list(skill_domains.get("secondary_domains", []))

        enterprise = EnterpriseExposure.NONE
        if _ENTERPRISE_SIGNALS.search(corpus):
            enterprise = EnterpriseExposure.DEEP
            signals.append("deep_enterprise_language")
        elif _MODERATE_ENTERPRISE.search(corpus):
            enterprise = EnterpriseExposure.MODERATE
            signals.append("moderate_enterprise_language")
        elif parsed.years_experience and parsed.years_experience >= 8:
            enterprise = EnterpriseExposure.LIMITED
            signals.append("tenure_enterprise_prior")

        delivery_hits = len(_DELIVERY_SIGNALS.findall(corpus))
        delivery_orientation = min(1.0, 0.2 + delivery_hits * 0.12)

        archetype_scores: dict[CompanyArchetypeId, float] = {
            a: 0.0 for a in CompanyArchetypeId
        }
        for archetype_id, definition in COMPANY_ARCHETYPES.items():
            for sig in definition.exposure_signals + definition.scale_signals:
                if sig.lower() in corpus:
                    archetype_scores[archetype_id] += 1.0
                    signals.append(f"archetype:{archetype_id.value}")

        # Role-family-informed archetype boost (deterministic)
        role_scores = self._score_role_families(parsed)
        top_roles = sorted(role_scores.items(), key=lambda x: -x[1])[:2]
        for role_id, _ in top_roles:
            if role_id in (
                RoleFamilyId.PROGRAM_LEADERSHIP,
                RoleFamilyId.ENTERPRISE_DELIVERY,
            ):
                archetype_scores[CompanyArchetypeId.GLOBAL_ENTERPRISE] += 0.5
                archetype_scores[CompanyArchetypeId.MID_MARKET_ENTERPRISE] += 0.3
            if role_id == RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT:
                archetype_scores[CompanyArchetypeId.TECH_SCALE_UP] += 0.4
                archetype_scores[CompanyArchetypeId.PRODUCT_LED_SAAS] += 0.3
            if role_id == RoleFamilyId.AI_TRANSFORMATION:
                archetype_scores[CompanyArchetypeId.PRODUCT_LED_SAAS] += 0.3
                archetype_scores[CompanyArchetypeId.REGULATED_INDUSTRY] += 0.2

        ranked_archetypes = sorted(
            archetype_scores.items(), key=lambda x: -x[1]
        )
        likely = [
            a for a, s in ranked_archetypes[:4] if s > 0
        ] or [CompanyArchetypeId.MID_MARKET_ENTERPRISE]

        return DomainResult(
            primary_domains=primary,
            secondary_domains=secondary,
            enterprise_experience=enterprise,
            delivery_orientation=round(delivery_orientation, 2),
            company_archetypes=likely,
            signals=signals,
        )

    def _score_role_families(self, parsed: ParsedResume) -> dict[RoleFamilyId, float]:
        text = parsed.raw_text.lower()
        titles = " ".join(parsed.job_titles).lower()
        scores: dict[RoleFamilyId, float] = {}
        for family_id, definition in ROLE_FAMILIES.items():
            score = 0.0
            for title in definition.canonical_titles:
                if title in titles or title in text:
                    score += 2.0
            for sig in definition.title_signals:
                if sig in titles:
                    score += 1.5
            scores[family_id] = score
        return scores
