"""Benchmark: enterprise architecture delivery lead."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Dana Wright | dana.wright@email.com

EXPERIENCE
Enterprise Architecture Lead | ArchCorp | 2015 – Present
• Owned reference architecture and integration architecture for enterprise systems
• Chaired architecture review board and solution architecture standards
• TOGAF-based target state and API integration patterns across domains
• Architecture program manager for platform and cloud initiatives

Solution Delivery Architect | IntegrateCo | 2010 – 2015
• Enterprise architecture, solution architecture, and technical governance

SKILLS
TOGAF, enterprise architecture, solution architecture, API, integration, architecture review board
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="enterprise_architect",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.ENTERPRISE_ARCHITECTURE_DELIVERY,
    expected_adjacent=(
        RoleFamilyId.PLATFORM_MODERNIZATION,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
    ),
    forbidden_families=(
        RoleFamilyId.SOFTWARE_ENGINEERING,
        RoleFamilyId.HR,
        RoleFamilyId.SALES,
        RoleFamilyId.FINANCE,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("architecture_coordination", 0.12, 0.75),
        CapabilityTraitRange("enterprise_governance", 0.08, 0.50),
        CapabilityTraitRange("technical_execution", 0.05, 0.45),
        CapabilityTraitRange("engineering_depth", 0.0, 0.35),
    ),
    description="Architecture lead; software engineering primary must not win.",
)
