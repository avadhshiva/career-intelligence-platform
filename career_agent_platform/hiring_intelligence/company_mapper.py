"""Static company hiring profiles for market intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompanyProfile:
    company: str
    industries: tuple[str, ...]
    dominant_hiring_dimensions: tuple[str, ...]
    typical_role_families: tuple[str, ...]
    ai_maturity: str
    governance_intensity: float
    transformation_intensity: float
    hiring_momentum: str = "Stable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "industries": list(self.industries),
            "dominant_hiring_dimensions": list(self.dominant_hiring_dimensions),
            "typical_role_families": list(self.typical_role_families),
            "ai_maturity": self.ai_maturity,
            "governance_intensity": self.governance_intensity,
            "transformation_intensity": self.transformation_intensity,
            "hiring_momentum": self.hiring_momentum,
        }


COMPANY_PROFILES: dict[str, CompanyProfile] = {
    "Walmart Global Tech": CompanyProfile(
        company="Walmart Global Tech",
        industries=("Retail", "Enterprise Technology"),
        dominant_hiring_dimensions=("delivery", "governance", "transformation"),
        typical_role_families=("technical_program_management", "enterprise_delivery", "ai_transformation"),
        ai_maturity="practitioner",
        governance_intensity=0.82,
        transformation_intensity=0.78,
        hiring_momentum="High",
    ),
    "Lowe's": CompanyProfile(
        company="Lowe's India",
        industries=("Retail", "Enterprise Technology"),
        dominant_hiring_dimensions=("delivery", "governance", "platform"),
        typical_role_families=("enterprise_delivery", "release_governance", "technical_program_management"),
        ai_maturity="pilot",
        governance_intensity=0.76,
        transformation_intensity=0.70,
        hiring_momentum="Growing",
    ),
    "Tesco": CompanyProfile(
        company="Tesco",
        industries=("Retail", "Enterprise Technology"),
        dominant_hiring_dimensions=("delivery", "governance", "operations"),
        typical_role_families=("enterprise_delivery", "program_leadership", "release_governance"),
        ai_maturity="pilot",
        governance_intensity=0.74,
        transformation_intensity=0.65,
        hiring_momentum="Stable",
    ),
    "Target": CompanyProfile(
        company="Target",
        industries=("Retail", "Enterprise Technology"),
        dominant_hiring_dimensions=("delivery", "platform", "governance"),
        typical_role_families=("technical_program_management", "enterprise_delivery", "platform_modernization"),
        ai_maturity="practitioner",
        governance_intensity=0.70,
        transformation_intensity=0.72,
        hiring_momentum="Growing",
    ),
    "JP Morgan": CompanyProfile(
        company="JP Morgan",
        industries=("Financial Services",),
        dominant_hiring_dimensions=("governance", "architecture", "delivery"),
        typical_role_families=("release_governance", "technical_program_management", "enterprise_architecture_delivery"),
        ai_maturity="practitioner",
        governance_intensity=0.90,
        transformation_intensity=0.68,
        hiring_momentum="High",
    ),
    "LSEG": CompanyProfile(
        company="LSEG",
        industries=("Financial Services", "Technology"),
        dominant_hiring_dimensions=("governance", "delivery", "transformation"),
        typical_role_families=("release_governance", "enterprise_delivery", "ai_transformation"),
        ai_maturity="practitioner",
        governance_intensity=0.86,
        transformation_intensity=0.74,
        hiring_momentum="Growing",
    ),
    "ServiceNow": CompanyProfile(
        company="ServiceNow",
        industries=("Technology", "Enterprise SaaS"),
        dominant_hiring_dimensions=("platform", "delivery", "transformation"),
        typical_role_families=("technical_program_management", "ai_program_management", "platform_modernization"),
        ai_maturity="transformation_lead",
        governance_intensity=0.62,
        transformation_intensity=0.85,
        hiring_momentum="High",
    ),
    "SAP": CompanyProfile(
        company="SAP",
        industries=("Technology", "Enterprise Software"),
        dominant_hiring_dimensions=("delivery", "transformation", "governance"),
        typical_role_families=("enterprise_delivery", "cloud_transformation", "program_leadership"),
        ai_maturity="practitioner",
        governance_intensity=0.72,
        transformation_intensity=0.80,
        hiring_momentum="Stable",
    ),
    "Microsoft": CompanyProfile(
        company="Microsoft",
        industries=("Technology",),
        dominant_hiring_dimensions=("platform", "architecture", "transformation"),
        typical_role_families=("technical_program_management", "ai_transformation", "cloud_transformation"),
        ai_maturity="transformation_lead",
        governance_intensity=0.68,
        transformation_intensity=0.88,
        hiring_momentum="High",
    ),
    "Deloitte": CompanyProfile(
        company="Deloitte",
        industries=("Consulting", "Professional Services"),
        dominant_hiring_dimensions=("delivery", "governance", "transformation"),
        typical_role_families=("enterprise_delivery", "program_leadership", "ai_transformation"),
        ai_maturity="practitioner",
        governance_intensity=0.78,
        transformation_intensity=0.82,
        hiring_momentum="Growing",
    ),
    "EY": CompanyProfile(
        company="EY",
        industries=("Consulting", "Professional Services"),
        dominant_hiring_dimensions=("governance", "delivery", "transformation"),
        typical_role_families=("program_leadership", "enterprise_delivery", "ai_transformation"),
        ai_maturity="practitioner",
        governance_intensity=0.80,
        transformation_intensity=0.79,
        hiring_momentum="Stable",
    ),
    "Accenture": CompanyProfile(
        company="Accenture",
        industries=("Consulting", "Technology Services"),
        dominant_hiring_dimensions=("delivery", "transformation", "governance"),
        typical_role_families=("enterprise_delivery", "ai_transformation", "cloud_transformation"),
        ai_maturity="transformation_lead",
        governance_intensity=0.75,
        transformation_intensity=0.86,
        hiring_momentum="High",
    ),
    "Fractal": CompanyProfile(
        company="Fractal",
        industries=("Technology", "AI Services"),
        dominant_hiring_dimensions=("transformation", "platform", "delivery"),
        typical_role_families=("ai_transformation", "ai_program_management", "technical_program_management"),
        ai_maturity="transformation_lead",
        governance_intensity=0.55,
        transformation_intensity=0.92,
        hiring_momentum="Growing",
    ),
    "Turing": CompanyProfile(
        company="Turing",
        industries=("Technology", "Talent Platform"),
        dominant_hiring_dimensions=("delivery", "platform", "transformation"),
        typical_role_families=("technical_program_management", "enterprise_delivery", "ai_program_management"),
        ai_maturity="practitioner",
        governance_intensity=0.50,
        transformation_intensity=0.70,
        hiring_momentum="Growing",
    ),
    "Observe.AI": CompanyProfile(
        company="Observe.AI",
        industries=("Technology", "AI SaaS"),
        dominant_hiring_dimensions=("platform", "transformation", "delivery"),
        typical_role_families=("ai_program_management", "technical_program_management", "product_delivery"),
        ai_maturity="transformation_lead",
        governance_intensity=0.48,
        transformation_intensity=0.90,
        hiring_momentum="High",
    ),
}


def lookup_company(name: str) -> CompanyProfile | None:
    from job_sources.company_registry import resolve_company

    canonical, _, company_type = resolve_company(company=name, raw_text=name)
    key = canonical.lower()
    for company, profile in COMPANY_PROFILES.items():
        if company.lower() == key or profile.company.lower() == key:
            return profile
    for company, profile in COMPANY_PROFILES.items():
        if key in company.lower() or key in profile.company.lower():
            return profile
    # Fuzzy via registry canonical without seeded profile
    if canonical != "Enterprise Technology Organization":
        return CompanyProfile(
            company=canonical,
            industries=(company_type,),
            dominant_hiring_dimensions=("delivery", "governance"),
            typical_role_families=("enterprise_delivery",),
            ai_maturity="pilot",
            governance_intensity=0.65,
            transformation_intensity=0.60,
        )
    return None
