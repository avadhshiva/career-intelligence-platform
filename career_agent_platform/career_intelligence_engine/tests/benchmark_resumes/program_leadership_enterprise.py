"""Benchmark: enterprise program leadership / portfolio director."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Alex Morgan | alex.morgan@email.com

EXPERIENCE
Program Director | Global Corp | 2017 – Present
• Directed enterprise portfolio with 15+ programs and $40M annual budget
• Owned portfolio governance, steering committee cadence, and benefits realization
• Led operating model redesign across global matrix organization
• Executive sponsor to C-suite for transformation portfolio

Senior Program Manager | Fabrikam | 2010 – 2017
• Program governance, cross-functional initiative portfolio, PMO standards

SKILLS
Portfolio management, PMP, governance, stakeholder management, transformation, benefits tracking
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="program_leadership_enterprise",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.PROGRAM_LEADERSHIP,
    expected_adjacent=(
        RoleFamilyId.ENTERPRISE_DELIVERY,
        RoleFamilyId.TRANSFORMATION_OFFICE,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
    ),
    forbidden_families=(
        RoleFamilyId.SOFTWARE_ENGINEERING,
        RoleFamilyId.OPERATIONS,
        RoleFamilyId.HR,
        RoleFamilyId.SALES,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("portfolio_management", 0.10, 0.55),
        CapabilityTraitRange("enterprise_governance", 0.08, 0.50),
        CapabilityTraitRange("executive_communication", 0.05, 0.55),
        CapabilityTraitRange("engineering_depth", 0.0, 0.25),
    ),
    description="Portfolio/program director; must not inflate operations or engineering.",
)
