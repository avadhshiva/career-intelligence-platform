"""Company environment archetypes — patterns, not company names."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import (
    CompanyArchetypeDefinition,
    CompanyArchetypeId,
)

COMPANY_ARCHETYPES: dict[CompanyArchetypeId, CompanyArchetypeDefinition] = {
    CompanyArchetypeId.GLOBAL_ENTERPRISE: CompanyArchetypeDefinition(
        id=CompanyArchetypeId.GLOBAL_ENTERPRISE,
        display_name="Global Enterprise",
        description="Fortune-scale, matrixed, multi-region operating environments.",
        exposure_signals=[
            "fortune",
            "global",
            "multi-region",
            "matrix organization",
            "enterprise-wide",
            "10000+ employees",
        ],
        scale_signals=["ftse", "dax", "global 2000", "multinational"],
    ),
    CompanyArchetypeId.MID_MARKET_ENTERPRISE: CompanyArchetypeDefinition(
        id=CompanyArchetypeId.MID_MARKET_ENTERPRISE,
        display_name="Mid-Market Enterprise",
        description="Established mid-size firms with formal PMO and governance.",
        exposure_signals=[
            "mid-market",
            "regional leader",
            "established enterprise",
            "pmo",
        ],
        scale_signals=["500-5000 employees", "regional headquarters"],
    ),
    CompanyArchetypeId.TECH_SCALE_UP: CompanyArchetypeDefinition(
        id=CompanyArchetypeId.TECH_SCALE_UP,
        display_name="Tech Scale-Up",
        description="High-growth technology companies scaling delivery and product.",
        exposure_signals=[
            "scale-up",
            "series b",
            "series c",
            "hypergrowth",
            "unicorn",
        ],
        scale_signals=["saas", "platform company", "product-led growth"],
    ),
    CompanyArchetypeId.CONSULTING_SERVICES: CompanyArchetypeDefinition(
        id=CompanyArchetypeId.CONSULTING_SERVICES,
        display_name="Consulting & Professional Services",
        description="Client-facing delivery across industries.",
        exposure_signals=[
            "consulting",
            "professional services",
            "client engagement",
            "billable",
            "practice area",
        ],
        scale_signals=["big four", "systems integrator", "advisory"],
    ),
    CompanyArchetypeId.REGULATED_INDUSTRY: CompanyArchetypeDefinition(
        id=CompanyArchetypeId.REGULATED_INDUSTRY,
        display_name="Regulated Industry",
        description="Heavily governed sectors: finance, healthcare, energy, telecom.",
        exposure_signals=[
            "regulated",
            "compliance",
            "hipaa",
            "sox",
            "gdpr",
            "fda",
            "pci-dss",
        ],
        scale_signals=["banking", "insurance", "pharma", "utilities"],
    ),
    CompanyArchetypeId.PUBLIC_SECTOR: CompanyArchetypeDefinition(
        id=CompanyArchetypeId.PUBLIC_SECTOR,
        display_name="Public Sector",
        description="Government and public institution environments.",
        exposure_signals=[
            "federal",
            "government",
            "public sector",
            "civil service",
            "agency",
        ],
        scale_signals=["clearance", "gs schedule", "state/local"],
    ),
    CompanyArchetypeId.STARTUP_VENTURE: CompanyArchetypeDefinition(
        id=CompanyArchetypeId.STARTUP_VENTURE,
        display_name="Startup / Early Venture",
        description="Early-stage, founder-led, minimal process maturity.",
        exposure_signals=[
            "startup",
            "seed stage",
            "series a",
            "founding team",
            "0-1",
        ],
        scale_signals=["early-stage", "venture-backed"],
    ),
    CompanyArchetypeId.PRODUCT_LED_SAAS: CompanyArchetypeDefinition(
        id=CompanyArchetypeId.PRODUCT_LED_SAAS,
        display_name="Product-Led SaaS",
        description="Subscription software businesses with product-centric delivery.",
        exposure_signals=[
            "saas",
            "subscription",
            "product-led",
            "b2b software",
            "arr",
            "nrr",
        ],
        scale_signals=["self-serve", "plg", "cloud-native"],
    ),
}


def get_company_archetype(archetype_id: CompanyArchetypeId) -> CompanyArchetypeDefinition:
    return COMPANY_ARCHETYPES[archetype_id]
