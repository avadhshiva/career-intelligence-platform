"""Benchmark: enterprise technical program manager."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Jordan Chen | jordan.chen@email.com

EXPERIENCE
Senior Technical Program Manager | Contoso | 2018 – Present
• Owned technical program delivery, SDLC alignment, and dependency management across 6 engineering teams
• Coordinated architecture reviews and engineering roadmap alignment for enterprise cloud migration
• Led GenAI pilot initiative with engineering and data science teams
• Cross-team coordination for Fortune 500 platform delivery across NA and EMEA
• Executive stakeholder management and technical steering committee reporting

Technical Program Manager | Northwind | 2013 – 2018
• Technical program management, PI planning, cross-functional engineering delivery

SKILLS
Program management, SDLC, agile, GenAI, AWS, governance, stakeholder management
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="technical_program_manager_enterprise",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
    expected_adjacent=(
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.ENTERPRISE_DELIVERY,
    ),
    forbidden_families=(
        RoleFamilyId.PRODUCT_DELIVERY,
        RoleFamilyId.PRODUCT_MANAGEMENT,
        RoleFamilyId.OPERATIONS,
        RoleFamilyId.HR,
    ),
    excluded_families=(
        RoleFamilyId.PRODUCT_DELIVERY,
        RoleFamilyId.PRODUCT_MANAGEMENT,
        RoleFamilyId.OPERATIONS,
        RoleFamilyId.ENTERPRISE_OPERATIONS,
    ),
    capability_traits=(
        CapabilityTraitRange("technical_execution", 0.12, 0.55),
        CapabilityTraitRange("release_governance", 0.08, 0.50),
        CapabilityTraitRange("architecture_coordination", 0.05, 0.45),
        CapabilityTraitRange("product_thinking", 0.0, 0.22),
        CapabilityTraitRange("operational_management", 0.0, 0.20),
    ),
    description="Enterprise TPM with release/SDLC focus; product and ops tracks must stay gated.",
)
