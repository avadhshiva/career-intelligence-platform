"""Benchmark: platform modernization lead."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Robin Shah | robin.shah@email.com

EXPERIENCE
Platform Modernization Lead | ModernizeCo | 2017 – Present
• Platform modernization owner for legacy decommission and platform migration program
• Legacy modernization with API modernization and platform migration standards
• Design authority for platform modernization guardrails and API integration
• Platform modernization lead driving legacy decommission across core platforms

Platform Modernization Manager | Infra Co | 2012 – 2017
• Platform modernization, legacy decommission, and platform migration for core systems

SKILLS
Platform modernization, legacy decommission, platform migration, API modernization, legacy modernization
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="platform_modernization_lead",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.PLATFORM_MODERNIZATION,
    acceptable_primaries=(
        RoleFamilyId.CLOUD_TRANSFORMATION,
        RoleFamilyId.ENTERPRISE_ARCHITECTURE_DELIVERY,
    ),
    expected_adjacent=(
        RoleFamilyId.CLOUD_TRANSFORMATION,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
    ),
    forbidden_families=(
        RoleFamilyId.PRODUCT_MANAGEMENT,
        RoleFamilyId.SALES,
        RoleFamilyId.FINANCE,
        RoleFamilyId.SOFTWARE_ENGINEERING,
    ),
    must_rank_in_top=((RoleFamilyId.PLATFORM_MODERNIZATION, 3),),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("technical_execution", 0.05, 0.60),
        CapabilityTraitRange("transformation_strategy", 0.05, 0.50),
        CapabilityTraitRange("architecture_coordination", 0.05, 0.50),
        CapabilityTraitRange("product_thinking", 0.0, 0.20),
    ),
    description=(
        "Platform modernization archetype; cloud may win primary when migration "
        "vocabulary co-occurs, but platform must remain top-3."
    ),
)
